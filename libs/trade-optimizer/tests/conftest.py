"""Pytest fixtures for trade-optimizer tests."""

import numpy as np
import pytest


@pytest.fixture
def sample_prices() -> np.ndarray:
    """Generate sample price data with clear arbitrage opportunities."""
    # Simulate 48 hours of hourly prices with day/night pattern
    np.random.seed(42)
    base_prices = np.array(
        [
            # Night (low prices) - hours 0-6
            25.0, 22.0, 20.0, 18.0, 20.0, 25.0, 30.0,
            # Morning ramp - hours 7-11
            45.0, 60.0, 75.0, 85.0, 90.0,
            # Afternoon peak - hours 12-17
            95.0, 100.0, 105.0, 100.0, 90.0, 80.0,
            # Evening - hours 18-23
            70.0, 65.0, 55.0, 45.0, 35.0, 28.0,
        ]
    )
    # Repeat for 2 days
    prices = np.tile(base_prices, 2)
    # Add some noise
    noise = np.random.normal(0, 3, len(prices))
    return prices + noise


@pytest.fixture
def volatile_prices() -> np.ndarray:
    """Generate highly volatile price data."""
    np.random.seed(123)
    n = 100
    # Random walk with high volatility
    returns = np.random.normal(0, 0.1, n)
    prices = 50 * np.exp(np.cumsum(returns))
    return prices


@pytest.fixture
def flat_prices() -> np.ndarray:
    """Generate flat prices with no arbitrage opportunity."""
    return np.full(48, 50.0)


@pytest.fixture
def battery_config():
    """Standard battery configuration for testing."""
    from trade_optimizer import BatteryConfig

    return BatteryConfig(
        capacity_mwh=100.0,
        max_charge_rate_mw=25.0,
        max_discharge_rate_mw=25.0,
        efficiency=0.9,
        min_soc=0.1,
        max_soc=0.9,
    )


@pytest.fixture
def small_battery_config():
    """Small battery for edge case testing."""
    from trade_optimizer import BatteryConfig

    return BatteryConfig(
        capacity_mwh=10.0,
        max_charge_rate_mw=5.0,
        max_discharge_rate_mw=5.0,
        efficiency=0.85,
        min_soc=0.2,
        max_soc=0.8,
    )
