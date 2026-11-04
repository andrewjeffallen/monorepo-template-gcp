"""Tests for the Python orchestration layer."""

import tempfile
from pathlib import Path

import numpy as np
import pytest


class TestPriceDataLoader:
    """Tests for PriceDataLoader."""

    def test_from_csv(self, sample_prices, tmp_path):
        """Test loading from CSV."""
        from trade_optimizer.orchestration import PriceDataLoader

        # Create test CSV
        csv_path = tmp_path / "prices.csv"
        import pandas as pd

        df = pd.DataFrame({"timestamp": range(len(sample_prices)), "price": sample_prices})
        df.to_csv(csv_path, index=False)

        # Load with data loader
        loader = PriceDataLoader()
        loaded_prices = loader.from_csv(csv_path, price_col="price")

        np.testing.assert_array_almost_equal(loaded_prices, sample_prices)

    def test_from_parquet(self, sample_prices, tmp_path):
        """Test loading from Parquet."""
        from trade_optimizer.orchestration import PriceDataLoader

        # Create test Parquet
        parquet_path = tmp_path / "prices.parquet"
        import polars as pl

        df = pl.DataFrame({"price": sample_prices})
        df.write_parquet(parquet_path)

        # Load with data loader
        loader = PriceDataLoader()
        loaded_prices = loader.from_parquet(parquet_path, price_col="price")

        np.testing.assert_array_almost_equal(loaded_prices, sample_prices)

    def test_from_pandas_dataframe(self, sample_prices):
        """Test extracting from pandas DataFrame."""
        from trade_optimizer.orchestration import PriceDataLoader
        import pandas as pd

        df = pd.DataFrame({"price": sample_prices})

        loader = PriceDataLoader()
        extracted = loader.from_dataframe(df, price_col="price")

        np.testing.assert_array_almost_equal(extracted, sample_prices)

    def test_from_polars_dataframe(self, sample_prices):
        """Test extracting from Polars DataFrame."""
        from trade_optimizer.orchestration import PriceDataLoader
        import polars as pl

        df = pl.DataFrame({"price": sample_prices})

        loader = PriceDataLoader()
        extracted = loader.from_dataframe(df, price_col="price")

        np.testing.assert_array_almost_equal(extracted, sample_prices)


class TestOptimizationPipeline:
    """Tests for OptimizationPipeline."""

    def test_run_basic(self, battery_config, sample_prices):
        """Test basic pipeline run."""
        from trade_optimizer.orchestration import OptimizationPipeline

        pipeline = OptimizationPipeline(battery_config=battery_config)
        results = pipeline.run(sample_prices, initial_soc=0.5)

        # Check result structure
        assert "schedule" in results
        assert "revenue" in results
        assert "final_soc" in results
        assert "signals" in results
        assert "metadata" in results

        # Check metadata
        assert results["metadata"]["num_periods"] == len(sample_prices)
        assert "optimization_time_ms" in results["metadata"]

    def test_run_with_timestamps(self, battery_config, sample_prices):
        """Test pipeline with timestamps."""
        from trade_optimizer.orchestration import OptimizationPipeline
        import pandas as pd

        pipeline = OptimizationPipeline(battery_config=battery_config)

        timestamps = pd.date_range("2024-01-01", periods=len(sample_prices), freq="h")
        results = pipeline.run(sample_prices, initial_soc=0.5, timestamps=timestamps.to_numpy())

        assert results["timestamps"] is not None
        assert len(results["timestamps"]) == len(sample_prices)

    def test_run_scenarios(self, battery_config):
        """Test multi-scenario optimization."""
        from trade_optimizer.orchestration import OptimizationPipeline

        pipeline = OptimizationPipeline(battery_config=battery_config)

        # Create 3 different scenarios
        np.random.seed(42)
        scenarios = [
            50 + 20 * np.random.randn(48) for _ in range(3)
        ]

        results = pipeline.run_scenarios(scenarios, initial_soc=0.5)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["metadata"]["scenario_id"] == i

    def test_analyze_results(self, battery_config, sample_prices):
        """Test result analysis."""
        from trade_optimizer.orchestration import OptimizationPipeline

        pipeline = OptimizationPipeline(battery_config=battery_config)
        results = pipeline.run(sample_prices, initial_soc=0.5)
        analysis = pipeline.analyze_results(results)

        # Check analysis metrics exist
        assert "total_revenue" in analysis
        assert "total_charged_mwh" in analysis
        assert "total_discharged_mwh" in analysis
        assert "avg_charge_price" in analysis
        assert "avg_discharge_price" in analysis
        assert "utilization_pct" in analysis


class TestResultExporter:
    """Tests for ResultExporter."""

    def test_to_parquet(self, battery_config, sample_prices, tmp_path):
        """Test exporting to Parquet."""
        from trade_optimizer.orchestration import OptimizationPipeline, ResultExporter

        pipeline = OptimizationPipeline(battery_config=battery_config)
        results = pipeline.run(sample_prices, initial_soc=0.5)

        exporter = ResultExporter(output_dir=tmp_path)
        output_path = exporter.to_parquet(results, "test_results.parquet")

        assert output_path.exists()

        # Verify contents
        import polars as pl

        df = pl.read_parquet(output_path)
        assert len(df) == len(sample_prices)
        assert "schedule_mw" in df.columns
        assert "price" in df.columns

    def test_to_csv(self, battery_config, sample_prices, tmp_path):
        """Test exporting to CSV."""
        from trade_optimizer.orchestration import OptimizationPipeline, ResultExporter

        pipeline = OptimizationPipeline(battery_config=battery_config)
        results = pipeline.run(sample_prices, initial_soc=0.5)

        exporter = ResultExporter(output_dir=tmp_path)
        output_path = exporter.to_csv(results, "test_results.csv")

        assert output_path.exists()

        # Verify contents
        import pandas as pd

        df = pd.read_csv(output_path)
        assert len(df) == len(sample_prices)

    def test_summary_report(self, battery_config, sample_prices, tmp_path):
        """Test generating summary report."""
        from trade_optimizer.orchestration import OptimizationPipeline, ResultExporter

        pipeline = OptimizationPipeline(battery_config=battery_config)
        results = pipeline.run(sample_prices, initial_soc=0.5)
        analysis = pipeline.analyze_results(results)

        exporter = ResultExporter(output_dir=tmp_path)
        report = exporter.summary_report(results, analysis)

        assert "BATTERY OPTIMIZATION REPORT" in report
        assert "Total Revenue" in report
        assert "MWh" in report


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    def test_full_workflow(self, battery_config, sample_prices, tmp_path):
        """Test complete workflow from data to export."""
        from trade_optimizer.orchestration import (
            OptimizationPipeline,
            PriceDataLoader,
            ResultExporter,
        )
        import pandas as pd

        # 1. Create input data
        input_csv = tmp_path / "input_prices.csv"
        timestamps = pd.date_range("2024-01-01", periods=len(sample_prices), freq="h")
        df = pd.DataFrame({"timestamp": timestamps, "price": sample_prices})
        df.to_csv(input_csv, index=False)

        # 2. Load data
        loader = PriceDataLoader()
        prices = loader.from_csv(input_csv, price_col="price")

        # 3. Run optimization
        pipeline = OptimizationPipeline(battery_config=battery_config)
        results = pipeline.run(prices, initial_soc=0.5, timestamps=timestamps.to_numpy())

        # 4. Analyze results
        analysis = pipeline.analyze_results(results)

        # 5. Export results
        exporter = ResultExporter(output_dir=tmp_path / "output")
        parquet_path = exporter.to_parquet(results)
        csv_path = exporter.to_csv(results)
        report = exporter.summary_report(results, analysis)

        # Verify outputs
        assert parquet_path.exists()
        assert csv_path.exists()
        assert len(report) > 100
        assert analysis["total_revenue"] > 0
