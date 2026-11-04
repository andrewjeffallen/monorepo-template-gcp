"""Trade and Battery Optimizer - High-performance optimization with Python orchestration.

This package provides:
- High-performance Rust optimization core via PyO3
- Python orchestration for data engineering pipelines
- Integration with pandas/polars for data manipulation

Example:
    >>> from trade_optimizer import BatteryOptimizer, BatteryConfig
    >>> import numpy as np
    >>>
    >>> config = BatteryConfig(
    ...     capacity_mwh=100.0,
    ...     max_charge_rate_mw=25.0,
    ...     max_discharge_rate_mw=25.0,
    ... )
    >>> optimizer = BatteryOptimizer(config)
    >>> prices = np.array([20.0, 30.0, 80.0, 60.0, 25.0])
    >>> schedule, revenue, final_soc = optimizer.optimize(prices, initial_soc=0.5)
"""

from trade_optimizer._core import (
    BatteryConfig,
    BatteryOptimizer,
    OptimizationResult,
    TradeOptimizer,
    find_arbitrage_opportunities,
    optimize_battery_schedule,
)
from trade_optimizer.orchestration import (
    OptimizationPipeline,
    PriceDataLoader,
    ResultExporter,
)

__version__ = "0.1.0"

__all__ = [
    # Rust core (via PyO3)
    "BatteryConfig",
    "BatteryOptimizer",
    "TradeOptimizer",
    "OptimizationResult",
    "optimize_battery_schedule",
    "find_arbitrage_opportunities",
    # Python orchestration
    "OptimizationPipeline",
    "PriceDataLoader",
    "ResultExporter",
]
