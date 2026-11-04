//! Battery storage optimization algorithms

use crate::types::{BatteryConfig, OptimizationResult, OptimizerError};
use rayon::prelude::*;

/// Battery dispatch optimizer using dynamic programming
pub struct BatteryOptimizer {
    config: BatteryConfig,
}

impl BatteryOptimizer {
    /// Create a new battery optimizer with the given configuration
    pub fn new(config: BatteryConfig) -> Self {
        Self { config }
    }

    /// Optimize battery dispatch schedule to maximize revenue
    ///
    /// Uses a greedy heuristic with look-ahead for fast optimization.
    /// For production use, consider implementing full dynamic programming
    /// or mixed-integer linear programming.
    ///
    /// # Arguments
    /// * `prices` - Price forecasts for each time period ($/MWh)
    /// * `initial_soc` - Initial state of charge (0.0 to 1.0)
    ///
    /// # Returns
    /// * `OptimizationResult` containing the optimal schedule and metrics
    pub fn optimize(
        &self,
        prices: &[f64],
        initial_soc: f64,
    ) -> Result<OptimizationResult, OptimizerError> {
        if prices.is_empty() {
            return Err(OptimizerError::InvalidInput(
                "Price array cannot be empty".to_string(),
            ));
        }

        if !(0.0..=1.0).contains(&initial_soc) {
            return Err(OptimizerError::InvalidInput(format!(
                "Initial SOC must be between 0 and 1, got {}",
                initial_soc
            )));
        }

        let n = prices.len();
        let mut schedule = vec![0.0; n];
        let mut soc = initial_soc;

        // Calculate price statistics for threshold-based decisions
        let mean_price: f64 = prices.iter().sum::<f64>() / n as f64;
        let price_std = (prices.iter().map(|p| (p - mean_price).powi(2)).sum::<f64>() / n as f64)
            .sqrt();

        let buy_threshold = mean_price - 0.5 * price_std;
        let sell_threshold = mean_price + 0.5 * price_std;

        // Greedy optimization with look-ahead
        for (i, &price) in prices.iter().enumerate() {
            let remaining = n - i;

            // Calculate available capacity
            let available_charge = (self.config.max_soc - soc) * self.config.capacity_mwh;
            let available_discharge = (soc - self.config.min_soc) * self.config.capacity_mwh;

            // Look ahead to find better opportunities
            let future_max = prices[i..].iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let future_min = prices[i..].iter().cloned().fold(f64::INFINITY, f64::min);

            // Decision logic
            let dispatch = if price <= buy_threshold && available_charge > 0.0 && remaining > 1 {
                // Charge when price is low (negative dispatch = charging)
                let charge_amount = self
                    .config
                    .max_charge_rate_mw
                    .min(available_charge)
                    .min(self.config.capacity_mwh * 0.25); // Limit to 25% per period
                -charge_amount
            } else if price >= sell_threshold && available_discharge > 0.0 {
                // Discharge when price is high
                let discharge_amount = self
                    .config
                    .max_discharge_rate_mw
                    .min(available_discharge)
                    .min(self.config.capacity_mwh * 0.25);
                discharge_amount
            } else if price >= future_max * 0.95 && available_discharge > 0.0 {
                // Opportunistic sell near peak
                let discharge_amount = self
                    .config
                    .max_discharge_rate_mw
                    .min(available_discharge)
                    .min(self.config.capacity_mwh * 0.2);
                discharge_amount
            } else if price <= future_min * 1.05 && available_charge > 0.0 && remaining > 1 {
                // Opportunistic buy near trough
                let charge_amount = self
                    .config
                    .max_charge_rate_mw
                    .min(available_charge)
                    .min(self.config.capacity_mwh * 0.2);
                -charge_amount
            } else {
                0.0
            };

            schedule[i] = dispatch;

            // Update SOC
            if dispatch > 0.0 {
                // Discharging
                soc -= dispatch / self.config.capacity_mwh;
            } else {
                // Charging (accounting for efficiency losses)
                soc -= dispatch * self.config.efficiency / self.config.capacity_mwh;
            }

            // Clamp SOC to valid range
            soc = soc.clamp(self.config.min_soc, self.config.max_soc);
        }

        // Calculate total revenue
        let total_revenue = self.calculate_revenue(prices, &schedule);

        Ok(OptimizationResult {
            schedule,
            total_revenue,
            final_soc: soc,
        })
    }

    /// Calculate revenue for a given schedule
    pub fn calculate_revenue(&self, prices: &[f64], schedule: &[f64]) -> f64 {
        prices
            .iter()
            .zip(schedule.iter())
            .map(|(&price, &dispatch)| {
                if dispatch > 0.0 {
                    // Revenue from selling
                    price * dispatch
                } else {
                    // Cost of buying (negative revenue)
                    price * dispatch // dispatch is negative, so this is a cost
                }
            })
            .sum()
    }

    /// Parallel optimization for multiple scenarios
    pub fn optimize_scenarios(
        &self,
        price_scenarios: &[Vec<f64>],
        initial_soc: f64,
    ) -> Vec<Result<OptimizationResult, OptimizerError>> {
        price_scenarios
            .par_iter()
            .map(|prices| self.optimize(prices, initial_soc))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    fn default_config() -> BatteryConfig {
        BatteryConfig {
            capacity_mwh: 100.0,
            max_charge_rate_mw: 25.0,
            max_discharge_rate_mw: 25.0,
            efficiency: 0.9,
            min_soc: 0.1,
            max_soc: 0.9,
        }
    }

    #[test]
    fn test_basic_arbitrage() {
        let optimizer = BatteryOptimizer::new(default_config());

        // Clear arbitrage opportunity: buy low, sell high
        let prices = vec![10.0, 10.0, 100.0, 100.0, 10.0];
        let result = optimizer.optimize(&prices, 0.5).unwrap();

        // Should generate positive revenue
        assert!(result.total_revenue > 0.0);
    }

    #[test]
    fn test_soc_constraints() {
        let optimizer = BatteryOptimizer::new(default_config());

        let prices = vec![100.0; 10]; // All high prices
        let result = optimizer.optimize(&prices, 0.5).unwrap();

        // Final SOC should respect minimum constraint
        assert!(result.final_soc >= 0.1 - 1e-6);
    }

    #[test]
    fn test_empty_prices_error() {
        let optimizer = BatteryOptimizer::new(default_config());
        let result = optimizer.optimize(&[], 0.5);
        assert!(result.is_err());
    }

    #[test]
    fn test_invalid_soc_error() {
        let optimizer = BatteryOptimizer::new(default_config());
        let result = optimizer.optimize(&[50.0], 1.5);
        assert!(result.is_err());
    }

    #[test]
    fn test_revenue_calculation() {
        let optimizer = BatteryOptimizer::new(default_config());

        let prices = vec![50.0, 100.0];
        let schedule = vec![-10.0, 10.0]; // Buy 10 MW at $50, sell at $100

        let revenue = optimizer.calculate_revenue(&prices, &schedule);
        // Revenue = -50*10 + 100*10 = -500 + 1000 = 500
        assert_relative_eq!(revenue, 500.0, epsilon = 1e-6);
    }
}
