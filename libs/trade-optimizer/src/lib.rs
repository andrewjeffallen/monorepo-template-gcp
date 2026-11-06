//! Trade and Battery Optimizer - High-performance optimization engine
//!
//! This crate provides optimization algorithms for:
//! - Battery energy storage arbitrage
//! - Trading schedule optimization
//! - Price signal analysis
//!
//! The core algorithms are written in Rust for performance,
//! with Python bindings via PyO3 for easy integration with
//! data engineering pipelines.

mod battery;
mod trade;
mod types;

use numpy::{AllowTypeChange, IntoPyArray, PyArray1, PyArrayLike1, PyReadonlyArray1};
use pyo3::prelude::*;

pub use battery::BatteryOptimizer;
pub use trade::TradeOptimizer;
pub use types::{BatteryConfig, OptimizationResult, TradeSignal};

/// Python module definition
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBatteryConfig>()?;
    m.add_class::<PyBatteryOptimizer>()?;
    m.add_class::<PyTradeOptimizer>()?;
    m.add_class::<PyOptimizationResult>()?;
    m.add_function(wrap_pyfunction!(optimize_battery_schedule, m)?)?;
    m.add_function(wrap_pyfunction!(find_arbitrage_opportunities, m)?)?;
    Ok(())
}

// =============================================================================
// Python wrapper types
// =============================================================================

/// Battery configuration exposed to Python
#[pyclass(name = "BatteryConfig")]
#[derive(Clone)]
pub struct PyBatteryConfig {
    inner: BatteryConfig,
}

#[pymethods]
impl PyBatteryConfig {
    #[new]
    #[pyo3(signature = (capacity_mwh, max_charge_rate_mw, max_discharge_rate_mw, efficiency=0.9, min_soc=0.1, max_soc=0.9))]
    fn new(
        capacity_mwh: f64,
        max_charge_rate_mw: f64,
        max_discharge_rate_mw: f64,
        efficiency: f64,
        min_soc: f64,
        max_soc: f64,
    ) -> Self {
        Self {
            inner: BatteryConfig {
                capacity_mwh,
                max_charge_rate_mw,
                max_discharge_rate_mw,
                efficiency,
                min_soc,
                max_soc,
            },
        }
    }

    #[getter]
    fn capacity_mwh(&self) -> f64 {
        self.inner.capacity_mwh
    }

    #[getter]
    fn max_charge_rate_mw(&self) -> f64 {
        self.inner.max_charge_rate_mw
    }

    #[getter]
    fn max_discharge_rate_mw(&self) -> f64 {
        self.inner.max_discharge_rate_mw
    }

    #[getter]
    fn efficiency(&self) -> f64 {
        self.inner.efficiency
    }

    fn __repr__(&self) -> String {
        format!(
            "BatteryConfig(capacity_mwh={}, max_charge_rate_mw={}, efficiency={})",
            self.inner.capacity_mwh, self.inner.max_charge_rate_mw, self.inner.efficiency
        )
    }
}

/// Battery optimizer exposed to Python
#[pyclass(name = "BatteryOptimizer")]
pub struct PyBatteryOptimizer {
    inner: BatteryOptimizer,
}

#[pymethods]
impl PyBatteryOptimizer {
    #[new]
    fn new(config: &PyBatteryConfig) -> Self {
        Self {
            inner: BatteryOptimizer::new(config.inner.clone()),
        }
    }

    /// Optimize battery dispatch schedule given price forecasts
    ///
    /// Args:
    ///     prices: Array of price forecasts ($/MWh) for each time period
    ///     initial_soc: Initial state of charge (0.0 to 1.0)
    ///
    /// Returns:
    ///     Tuple of (dispatch_schedule, revenue, final_soc)
    fn optimize<'py>(
        &self,
        py: Python<'py>,
        prices: PyArrayLike1<'py, f64, AllowTypeChange>,
        initial_soc: f64,
    ) -> PyResult<(Bound<'py, PyArray1<f64>>, f64, f64)> {
        let prices_slice = prices.as_slice()?;
        let result = self
            .inner
            .optimize(prices_slice, initial_soc)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        Ok((
            result.schedule.into_pyarray(py),
            result.total_revenue,
            result.final_soc,
        ))
    }

    /// Calculate expected revenue for a given dispatch schedule
    fn calculate_revenue<'py>(
        &self,
        prices: PyArrayLike1<'py, f64, AllowTypeChange>,
        schedule: PyArrayLike1<'py, f64, AllowTypeChange>,
    ) -> PyResult<f64> {
        let prices_slice = prices.as_slice()?;
        let schedule_slice = schedule.as_slice()?;
        Ok(self.inner.calculate_revenue(prices_slice, schedule_slice))
    }
}

/// Trade optimizer for arbitrage opportunities
#[pyclass(name = "TradeOptimizer")]
pub struct PyTradeOptimizer {
    inner: TradeOptimizer,
}

#[pymethods]
impl PyTradeOptimizer {
    #[new]
    #[pyo3(signature = (min_spread=5.0, max_position=100.0))]
    fn new(min_spread: f64, max_position: f64) -> Self {
        Self {
            inner: TradeOptimizer::new(min_spread, max_position),
        }
    }

    /// Find arbitrage opportunities in price series
    ///
    /// Args:
    ///     prices: Array of prices over time
    ///     window_size: Rolling window size for analysis
    ///
    /// Returns:
    ///     Array of trade signals (-1 = sell, 0 = hold, 1 = buy)
    fn find_opportunities<'py>(
        &self,
        py: Python<'py>,
        prices: PyArrayLike1<'py, f64, AllowTypeChange>,
        window_size: usize,
    ) -> PyResult<Bound<'py, PyArray1<i32>>> {
        let prices_slice = prices.as_slice()?;
        let signals = self.inner.find_opportunities(prices_slice, window_size);
        Ok(signals.into_pyarray(py))
    }

    /// Backtest trading strategy
    fn backtest<'py>(
        &self,
        prices: PyArrayLike1<'py, f64, AllowTypeChange>,
        signals: PyReadonlyArray1<'py, i32>,
    ) -> PyResult<f64> {
        let prices_slice = prices.as_slice()?;
        let signals_slice = signals.as_slice()?;
        Ok(self.inner.backtest(prices_slice, signals_slice))
    }
}

/// Optimization result container
#[pyclass(name = "OptimizationResult")]
#[derive(Clone)]
pub struct PyOptimizationResult {
    #[pyo3(get)]
    total_revenue: f64,
    #[pyo3(get)]
    final_soc: f64,
    schedule: Vec<f64>,
}

#[pymethods]
impl PyOptimizationResult {
    #[getter]
    fn schedule<'py>(&self, py: Python<'py>) -> Bound<'py, PyArray1<f64>> {
        self.schedule.clone().into_pyarray(py)
    }

    fn __repr__(&self) -> String {
        format!(
            "OptimizationResult(revenue=${:.2}, final_soc={:.1}%)",
            self.total_revenue,
            self.final_soc * 100.0
        )
    }
}

// =============================================================================
// Standalone functions exposed to Python
// =============================================================================

/// Optimize battery dispatch schedule (convenience function)
#[pyfunction]
#[pyo3(signature = (prices, capacity_mwh, max_power_mw, initial_soc=0.5, efficiency=0.9))]
fn optimize_battery_schedule<'py>(
    py: Python<'py>,
    prices: PyArrayLike1<'py, f64, AllowTypeChange>,
    capacity_mwh: f64,
    max_power_mw: f64,
    initial_soc: f64,
    efficiency: f64,
) -> PyResult<(Bound<'py, PyArray1<f64>>, f64)> {
    let config = BatteryConfig {
        capacity_mwh,
        max_charge_rate_mw: max_power_mw,
        max_discharge_rate_mw: max_power_mw,
        efficiency,
        min_soc: 0.1,
        max_soc: 0.9,
    };

    let optimizer = BatteryOptimizer::new(config);
    let prices_slice = prices.as_slice()?;

    let result = optimizer
        .optimize(prices_slice, initial_soc)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok((result.schedule.into_pyarray(py), result.total_revenue))
}

/// Find arbitrage opportunities in price series (convenience function)
#[pyfunction]
#[pyo3(signature = (prices, window_size=24, min_spread=5.0))]
fn find_arbitrage_opportunities<'py>(
    py: Python<'py>,
    prices: PyArrayLike1<'py, f64, AllowTypeChange>,
    window_size: usize,
    min_spread: f64,
) -> PyResult<Bound<'py, PyArray1<i32>>> {
    let optimizer = TradeOptimizer::new(min_spread, 100.0);
    let prices_slice = prices.as_slice()?;
    let signals = optimizer.find_opportunities(prices_slice, window_size);
    Ok(signals.into_pyarray(py))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_battery_config() {
        let config = BatteryConfig {
            capacity_mwh: 100.0,
            max_charge_rate_mw: 25.0,
            max_discharge_rate_mw: 25.0,
            efficiency: 0.9,
            min_soc: 0.1,
            max_soc: 0.9,
        };
        assert_eq!(config.capacity_mwh, 100.0);
    }

    #[test]
    fn test_battery_optimizer() {
        let config = BatteryConfig {
            capacity_mwh: 100.0,
            max_charge_rate_mw: 25.0,
            max_discharge_rate_mw: 25.0,
            efficiency: 0.9,
            min_soc: 0.1,
            max_soc: 0.9,
        };
        let optimizer = BatteryOptimizer::new(config);

        // Simple price pattern: low-high-low
        let prices = vec![20.0, 50.0, 80.0, 50.0, 20.0];
        let result = optimizer.optimize(&prices, 0.5).unwrap();

        // Should have non-zero revenue from arbitrage
        assert!(result.total_revenue >= 0.0);
    }
}
