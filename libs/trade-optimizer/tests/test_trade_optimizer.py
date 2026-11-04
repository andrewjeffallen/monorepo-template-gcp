"""Tests for the trade optimizer (Rust core via Python bindings)."""

import numpy as np
import pytest

from trade_optimizer import TradeOptimizer, find_arbitrage_opportunities


class TestTradeOptimizer:
    """Tests for the TradeOptimizer Rust implementation."""

    def test_create_optimizer(self):
        """Test optimizer creation with parameters."""
        optimizer = TradeOptimizer(min_spread=5.0, max_position=100.0)
        assert optimizer is not None

    def test_create_optimizer_defaults(self):
        """Test optimizer creation with default parameters."""
        optimizer = TradeOptimizer()
        assert optimizer is not None

    def test_find_opportunities_basic(self, sample_prices):
        """Test basic opportunity finding."""
        optimizer = TradeOptimizer(min_spread=5.0, max_position=100.0)
        signals = optimizer.find_opportunities(sample_prices, window_size=6)

        # Check output shape
        assert len(signals) == len(sample_prices)

        # Check signal values are valid
        assert all(s in [-1, 0, 1] for s in signals)

    def test_find_opportunities_detects_extremes(self):
        """Test that optimizer detects price extremes."""
        optimizer = TradeOptimizer(min_spread=5.0, max_position=100.0)

        # Clear pattern: stable then spike then stable
        prices = np.array([
            50.0, 50.0, 50.0, 50.0, 50.0,  # Window establishment
            50.0, 30.0, 70.0, 50.0,  # Drop then spike
        ])

        signals = optimizer.find_opportunities(prices, window_size=5)

        # Should have buy signal at low price (index 6, price 30)
        assert signals[6] == 1  # Buy

        # Should have sell signal at high price (index 7, price 70)
        assert signals[7] == -1  # Sell

    def test_find_opportunities_short_window(self):
        """Test behavior when window is larger than data."""
        optimizer = TradeOptimizer(min_spread=5.0, max_position=100.0)
        prices = np.array([50.0, 60.0])

        signals = optimizer.find_opportunities(prices, window_size=5)

        # Should return all holds when window > data
        assert all(s == 0 for s in signals)

    def test_backtest_profitable_strategy(self):
        """Test backtesting a profitable strategy."""
        optimizer = TradeOptimizer(min_spread=5.0, max_position=100.0)

        prices = np.array([100.0, 90.0, 110.0, 100.0])
        signals = np.array([0, 1, -1, 0], dtype=np.int32)  # Buy at 90, sell at 110

        profit = optimizer.backtest(prices, signals)

        # Should be profitable
        assert profit > 0

    def test_backtest_losing_strategy(self):
        """Test backtesting a losing strategy."""
        optimizer = TradeOptimizer(min_spread=5.0, max_position=100.0)

        prices = np.array([100.0, 110.0, 90.0, 100.0])
        signals = np.array([0, 1, -1, 0], dtype=np.int32)  # Buy high, sell low

        profit = optimizer.backtest(prices, signals)

        # Should be negative
        assert profit < 0


class TestFindArbitrageOpportunities:
    """Tests for the convenience function."""

    def test_find_arbitrage_basic(self, sample_prices):
        """Test basic arbitrage detection."""
        signals = find_arbitrage_opportunities(sample_prices)

        assert len(signals) == len(sample_prices)
        assert all(s in [-1, 0, 1] for s in signals)

    def test_find_arbitrage_custom_params(self, sample_prices):
        """Test with custom parameters."""
        signals = find_arbitrage_opportunities(
            sample_prices,
            window_size=12,
            min_spread=10.0,
        )

        assert len(signals) == len(sample_prices)

    def test_find_arbitrage_volatile(self, volatile_prices):
        """Test with volatile prices generates signals."""
        signals = find_arbitrage_opportunities(volatile_prices, window_size=10)

        # Should have some non-zero signals in volatile market
        non_zero = np.sum(signals != 0)
        assert non_zero > 0


class TestCrossLanguageConsistency:
    """Tests ensuring Rust and Python produce consistent results."""

    def test_optimizer_types_match(self, battery_config, sample_prices):
        """Test that Rust returns correct Python types."""
        from trade_optimizer import BatteryOptimizer

        optimizer = BatteryOptimizer(battery_config)
        schedule, revenue, final_soc = optimizer.optimize(sample_prices, 0.5)

        # Check NumPy array type
        assert isinstance(schedule, np.ndarray)
        assert schedule.dtype == np.float64

        # Check Python float types
        assert isinstance(revenue, float)
        assert isinstance(final_soc, float)

    def test_numpy_array_handling(self, battery_config):
        """Test that NumPy arrays are handled correctly."""
        from trade_optimizer import BatteryOptimizer

        optimizer = BatteryOptimizer(battery_config)

        # Test with different NumPy array types
        prices_f64 = np.array([50.0, 100.0, 50.0], dtype=np.float64)
        prices_f32 = np.array([50.0, 100.0, 50.0], dtype=np.float32)

        # Should handle float64
        schedule1, _, _ = optimizer.optimize(prices_f64, 0.5)
        assert len(schedule1) == 3

        # Should also handle float32 (converted internally)
        schedule2, _, _ = optimizer.optimize(prices_f32, 0.5)
        assert len(schedule2) == 3
