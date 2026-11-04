"""Data engineering and orchestration layer for the optimizer.

This module provides high-level abstractions for:
- Loading and preprocessing price data
- Running optimization pipelines
- Exporting and analyzing results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl

from trade_optimizer._core import (
    BatteryConfig,
    BatteryOptimizer,
    TradeOptimizer,
)


@dataclass
class PriceDataLoader:
    """Load and preprocess price data from various sources."""

    timezone: str = "UTC"
    resample_freq: str | None = None

    def from_csv(self, path: str | Path, price_col: str = "price") -> np.ndarray:
        """Load prices from a CSV file.

        Args:
            path: Path to CSV file
            price_col: Name of the price column

        Returns:
            NumPy array of prices
        """
        import pandas as pd

        df = pd.read_csv(path)
        return df[price_col].to_numpy()

    def from_parquet(self, path: str | Path, price_col: str = "price") -> np.ndarray:
        """Load prices from a Parquet file using Polars for speed."""
        import polars as pl

        df = pl.read_parquet(path)
        return df[price_col].to_numpy()

    def from_dataframe(
        self,
        df: pd.DataFrame | pl.DataFrame,
        price_col: str = "price",
    ) -> np.ndarray:
        """Extract prices from a DataFrame."""
        if hasattr(df, "to_numpy"):
            # pandas DataFrame
            return df[price_col].to_numpy()
        else:
            # polars DataFrame
            return df[price_col].to_numpy()

    def resample_prices(
        self,
        prices: np.ndarray,
        timestamps: np.ndarray,
        target_freq: str = "1h",
    ) -> tuple[np.ndarray, np.ndarray]:
        """Resample price data to target frequency.

        Args:
            prices: Array of prices
            timestamps: Array of timestamps
            target_freq: Target frequency (pandas offset string)

        Returns:
            Tuple of (resampled_prices, resampled_timestamps)
        """
        import pandas as pd

        df = pd.DataFrame({"price": prices, "timestamp": timestamps})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")

        resampled = df.resample(target_freq).mean()
        return resampled["price"].to_numpy(), resampled.index.to_numpy()


@dataclass
class OptimizationPipeline:
    """High-level pipeline for running battery optimization.

    This class orchestrates the full optimization workflow:
    1. Load and preprocess data
    2. Run optimization
    3. Analyze and export results

    Example:
        >>> pipeline = OptimizationPipeline(
        ...     battery_config=BatteryConfig(100.0, 25.0, 25.0),
        ... )
        >>> results = pipeline.run(prices, initial_soc=0.5)
        >>> pipeline.export_results(results, "output/results.parquet")
    """

    battery_config: BatteryConfig
    trade_config: dict[str, float] = field(
        default_factory=lambda: {"min_spread": 5.0, "max_position": 100.0}
    )

    def __post_init__(self):
        self.battery_optimizer = BatteryOptimizer(self.battery_config)
        self.trade_optimizer = TradeOptimizer(**self.trade_config)
        self.data_loader = PriceDataLoader()

    def run(
        self,
        prices: np.ndarray,
        initial_soc: float = 0.5,
        timestamps: np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Run the optimization pipeline.

        Args:
            prices: Array of price forecasts
            initial_soc: Initial battery state of charge
            timestamps: Optional timestamps for the prices

        Returns:
            Dictionary containing optimization results and metadata
        """
        start_time = datetime.now()

        # Run battery optimization
        schedule, revenue, final_soc = self.battery_optimizer.optimize(prices, initial_soc)

        # Find arbitrage signals for comparison
        signals = self.trade_optimizer.find_opportunities(prices, window_size=24)

        end_time = datetime.now()

        return {
            "schedule": schedule,
            "revenue": revenue,
            "final_soc": final_soc,
            "signals": signals,
            "prices": prices,
            "timestamps": timestamps,
            "metadata": {
                "initial_soc": initial_soc,
                "battery_capacity_mwh": self.battery_config.capacity_mwh,
                "optimization_time_ms": (end_time - start_time).total_seconds() * 1000,
                "num_periods": len(prices),
            },
        }

    def run_scenarios(
        self,
        price_scenarios: list[np.ndarray],
        initial_soc: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Run optimization for multiple price scenarios.

        Useful for Monte Carlo simulation or scenario analysis.

        Args:
            price_scenarios: List of price arrays (one per scenario)
            initial_soc: Initial battery state of charge

        Returns:
            List of result dictionaries
        """
        results = []
        for i, prices in enumerate(price_scenarios):
            result = self.run(prices, initial_soc)
            result["metadata"]["scenario_id"] = i
            results.append(result)
        return results

    def analyze_results(self, results: dict[str, Any]) -> dict[str, float]:
        """Analyze optimization results.

        Args:
            results: Results from run()

        Returns:
            Dictionary of analysis metrics
        """
        schedule = results["schedule"]
        prices = results["prices"]

        # Calculate metrics
        total_charged = -np.sum(schedule[schedule < 0])
        total_discharged = np.sum(schedule[schedule > 0])

        avg_charge_price = np.mean(prices[schedule < 0]) if np.any(schedule < 0) else 0
        avg_discharge_price = np.mean(prices[schedule > 0]) if np.any(schedule > 0) else 0

        return {
            "total_revenue": results["revenue"],
            "total_charged_mwh": total_charged,
            "total_discharged_mwh": total_discharged,
            "avg_charge_price": avg_charge_price,
            "avg_discharge_price": avg_discharge_price,
            "price_spread_captured": avg_discharge_price - avg_charge_price,
            "num_charge_periods": int(np.sum(schedule < 0)),
            "num_discharge_periods": int(np.sum(schedule > 0)),
            "utilization_pct": (np.sum(schedule != 0) / len(schedule)) * 100,
        }


@dataclass
class ResultExporter:
    """Export optimization results to various formats."""

    output_dir: str | Path = "output"

    def __post_init__(self):
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_parquet(
        self,
        results: dict[str, Any],
        filename: str = "optimization_results.parquet",
    ) -> Path:
        """Export results to Parquet format.

        Args:
            results: Results from OptimizationPipeline.run()
            filename: Output filename

        Returns:
            Path to the output file
        """
        import polars as pl

        # Build DataFrame
        data = {
            "schedule_mw": results["schedule"],
            "price": results["prices"],
            "signal": results["signals"],
        }

        if results["timestamps"] is not None:
            data["timestamp"] = results["timestamps"]

        df = pl.DataFrame(data)

        output_path = self.output_dir / filename
        df.write_parquet(output_path)

        return output_path

    def to_csv(
        self,
        results: dict[str, Any],
        filename: str = "optimization_results.csv",
    ) -> Path:
        """Export results to CSV format."""
        import pandas as pd

        data = {
            "schedule_mw": results["schedule"],
            "price": results["prices"],
            "signal": results["signals"],
        }

        if results["timestamps"] is not None:
            data["timestamp"] = results["timestamps"]

        df = pd.DataFrame(data)

        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)

        return output_path

    def summary_report(self, results: dict[str, Any], analysis: dict[str, float]) -> str:
        """Generate a text summary report.

        Args:
            results: Results from OptimizationPipeline.run()
            analysis: Analysis from OptimizationPipeline.analyze_results()

        Returns:
            Formatted summary string
        """
        return f"""
================================================================================
                        BATTERY OPTIMIZATION REPORT
================================================================================

Configuration:
  Battery Capacity:     {results['metadata']['battery_capacity_mwh']:.1f} MWh
  Initial SOC:          {results['metadata']['initial_soc']*100:.1f}%
  Periods Optimized:    {results['metadata']['num_periods']}
  Optimization Time:    {results['metadata']['optimization_time_ms']:.2f} ms

Results:
  Total Revenue:        ${analysis['total_revenue']:,.2f}
  Final SOC:            {results['final_soc']*100:.1f}%

Energy Summary:
  Total Charged:        {analysis['total_charged_mwh']:.2f} MWh
  Total Discharged:     {analysis['total_discharged_mwh']:.2f} MWh
  Charge Periods:       {analysis['num_charge_periods']}
  Discharge Periods:    {analysis['num_discharge_periods']}
  Utilization:          {analysis['utilization_pct']:.1f}%

Price Analysis:
  Avg Charge Price:     ${analysis['avg_charge_price']:.2f}/MWh
  Avg Discharge Price:  ${analysis['avg_discharge_price']:.2f}/MWh
  Spread Captured:      ${analysis['price_spread_captured']:.2f}/MWh

================================================================================
"""
