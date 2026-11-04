"""Tests for the battery optimizer (Rust core via Python bindings)."""

import numpy as np
import pytest

from trade_optimizer import BatteryConfig, BatteryOptimizer


class TestBatteryConfig:
    """Tests for BatteryConfig dataclass."""

    def test_create_config(self):
        """Test basic config creation."""
        config = BatteryConfig(
            capacity_mwh=100.0,
            max_charge_rate_mw=25.0,
            max_discharge_rate_mw=25.0,
        )
        assert config.capacity_mwh == 100.0
        assert config.max_charge_rate_mw == 25.0

    def test_config_defaults(self):
        """Test config with default values."""
        config = BatteryConfig(
            capacity_mwh=50.0,
            max_charge_rate_mw=10.0,
            max_discharge_rate_mw=10.0,
        )
        # Should have default efficiency
        assert config.efficiency == 0.9

    def test_config_repr(self):
        """Test config string representation."""
        config = BatteryConfig(100.0, 25.0, 25.0)
        repr_str = repr(config)
        assert "100" in repr_str
        assert "BatteryConfig" in repr_str


class TestBatteryOptimizer:
    """Tests for the BatteryOptimizer Rust implementation."""

    def test_optimize_basic(self, battery_config, sample_prices):
        """Test basic optimization returns valid results."""
        optimizer = BatteryOptimizer(battery_config)
        schedule, revenue, final_soc = optimizer.optimize(sample_prices, initial_soc=0.5)

        # Check shapes
        assert len(schedule) == len(sample_prices)

        # Check types
        assert isinstance(schedule, np.ndarray)
        assert isinstance(revenue, float)
        assert isinstance(final_soc, float)

        # SOC should be within bounds
        assert 0.1 <= final_soc <= 0.9

    def test_optimize_generates_revenue(self, battery_config, sample_prices):
        """Test that optimizer generates positive revenue with price spread."""
        optimizer = BatteryOptimizer(battery_config)
        _, revenue, _ = optimizer.optimize(sample_prices, initial_soc=0.5)

        # With clear price spread, should generate positive revenue
        assert revenue > 0

    def test_optimize_respects_soc_limits(self, battery_config, sample_prices):
        """Test that optimization respects SOC limits."""
        optimizer = BatteryOptimizer(battery_config)

        # Start at minimum SOC
        schedule, _, final_soc = optimizer.optimize(sample_prices, initial_soc=0.1)
        assert final_soc >= 0.1 - 1e-6

        # Start at maximum SOC
        schedule, _, final_soc = optimizer.optimize(sample_prices, initial_soc=0.9)
        assert final_soc <= 0.9 + 1e-6

    def test_optimize_flat_prices(self, battery_config, flat_prices):
        """Test optimization with flat prices (no arbitrage)."""
        optimizer = BatteryOptimizer(battery_config)
        schedule, revenue, _ = optimizer.optimize(flat_prices, initial_soc=0.5)

        # With flat prices, trading should be minimal
        # Revenue could be near zero or slightly negative due to efficiency losses
        assert revenue <= 100  # Should not be significant

    def test_calculate_revenue(self, battery_config):
        """Test manual revenue calculation."""
        optimizer = BatteryOptimizer(battery_config)

        prices = np.array([50.0, 100.0])
        schedule = np.array([-10.0, 10.0])  # Buy 10 at $50, sell 10 at $100

        revenue = optimizer.calculate_revenue(prices, schedule)

        # Revenue = -50*10 + 100*10 = 500
        assert abs(revenue - 500.0) < 1e-6

    def test_optimize_empty_prices_raises(self, battery_config):
        """Test that empty prices array raises error."""
        optimizer = BatteryOptimizer(battery_config)

        with pytest.raises(ValueError):
            optimizer.optimize(np.array([]), initial_soc=0.5)

    def test_optimize_invalid_soc_raises(self, battery_config, sample_prices):
        """Test that invalid initial SOC raises error."""
        optimizer = BatteryOptimizer(battery_config)

        with pytest.raises(ValueError):
            optimizer.optimize(sample_prices, initial_soc=1.5)

        with pytest.raises(ValueError):
            optimizer.optimize(sample_prices, initial_soc=-0.1)


class TestBatteryOptimizerPerformance:
    """Performance tests for the Rust optimizer."""

    @pytest.mark.benchmark
    def test_optimize_large_dataset(self, battery_config):
        """Test optimization on large dataset (1 year of hourly data)."""
        np.random.seed(42)
        # 1 year of hourly prices
        prices = 50 + 30 * np.sin(np.linspace(0, 365 * 2 * np.pi, 8760)) + \
                 np.random.normal(0, 10, 8760)

        optimizer = BatteryOptimizer(battery_config)

        import time
        start = time.perf_counter()
        schedule, revenue, final_soc = optimizer.optimize(prices, initial_soc=0.5)
        elapsed = time.perf_counter() - start

        # Should complete quickly (< 100ms for 8760 periods)
        assert elapsed < 0.1
        assert len(schedule) == 8760

    def test_optimize_consistency(self, battery_config, sample_prices):
        """Test that optimization is deterministic."""
        optimizer = BatteryOptimizer(battery_config)

        results = [
            optimizer.optimize(sample_prices, initial_soc=0.5)
            for _ in range(5)
        ]

        # All results should be identical
        for i in range(1, 5):
            np.testing.assert_array_equal(results[0][0], results[i][0])
            assert results[0][1] == results[i][1]
            assert results[0][2] == results[i][2]
