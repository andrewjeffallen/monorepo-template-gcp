//! Common types for the trade optimizer

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Battery storage configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatteryConfig {
    /// Total energy capacity in MWh
    pub capacity_mwh: f64,
    /// Maximum charging rate in MW
    pub max_charge_rate_mw: f64,
    /// Maximum discharging rate in MW
    pub max_discharge_rate_mw: f64,
    /// Round-trip efficiency (0.0 to 1.0)
    pub efficiency: f64,
    /// Minimum state of charge (0.0 to 1.0)
    pub min_soc: f64,
    /// Maximum state of charge (0.0 to 1.0)
    pub max_soc: f64,
}

impl Default for BatteryConfig {
    fn default() -> Self {
        Self {
            capacity_mwh: 100.0,
            max_charge_rate_mw: 25.0,
            max_discharge_rate_mw: 25.0,
            efficiency: 0.9,
            min_soc: 0.1,
            max_soc: 0.9,
        }
    }
}

/// Result of an optimization run
#[derive(Debug, Clone)]
pub struct OptimizationResult {
    /// Dispatch schedule (positive = discharge, negative = charge)
    pub schedule: Vec<f64>,
    /// Total revenue/profit from the schedule
    pub total_revenue: f64,
    /// Final state of charge
    pub final_soc: f64,
}

/// Trade signal for a given time period
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TradeSignal {
    /// Buy/charge signal
    Buy = 1,
    /// Hold/no action
    Hold = 0,
    /// Sell/discharge signal
    Sell = -1,
}

impl From<TradeSignal> for i32 {
    fn from(signal: TradeSignal) -> Self {
        match signal {
            TradeSignal::Buy => 1,
            TradeSignal::Hold => 0,
            TradeSignal::Sell => -1,
        }
    }
}

impl From<i32> for TradeSignal {
    fn from(val: i32) -> Self {
        match val {
            1 => TradeSignal::Buy,
            -1 => TradeSignal::Sell,
            _ => TradeSignal::Hold,
        }
    }
}

/// Errors that can occur during optimization
#[derive(Error, Debug)]
pub enum OptimizerError {
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    #[error("Invalid input data: {0}")]
    InvalidInput(String),

    #[error("Optimization failed to converge: {0}")]
    ConvergenceError(String),

    #[error("Constraint violation: {0}")]
    ConstraintViolation(String),
}
