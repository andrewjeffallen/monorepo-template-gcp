//! Trade signal generation and backtesting

use crate::types::TradeSignal;

/// Trade optimizer for generating arbitrage signals
pub struct TradeOptimizer {
    /// Minimum price spread to trigger a trade
    min_spread: f64,
    /// Maximum position size
    max_position: f64,
}

impl TradeOptimizer {
    /// Create a new trade optimizer
    pub fn new(min_spread: f64, max_position: f64) -> Self {
        Self {
            min_spread,
            max_position,
        }
    }

    /// Find arbitrage opportunities using a mean-reversion strategy
    ///
    /// Generates buy signals when price is below the rolling mean minus threshold,
    /// and sell signals when price is above the rolling mean plus threshold.
    ///
    /// # Arguments
    /// * `prices` - Historical price series
    /// * `window_size` - Rolling window size for mean calculation
    ///
    /// # Returns
    /// * Array of trade signals: 1 (buy), 0 (hold), -1 (sell)
    pub fn find_opportunities(&self, prices: &[f64], window_size: usize) -> Vec<i32> {
        if prices.len() < window_size {
            return vec![0; prices.len()];
        }

        let mut signals = vec![0; prices.len()];

        // Pre-calculate rolling statistics
        for i in window_size..prices.len() {
            let window = &prices[i - window_size..i];
            let mean: f64 = window.iter().sum::<f64>() / window_size as f64;
            let std = (window.iter().map(|p| (p - mean).powi(2)).sum::<f64>() / window_size as f64)
                .sqrt();

            let current_price = prices[i];
            let z_score = if std > 1e-6 {
                (current_price - mean) / std
            } else {
                // Flat window: any deviation is maximally significant; min_spread filters noise
                (current_price - mean) * f64::INFINITY
            };

            // Generate signals based on z-score and minimum spread
            let spread = (current_price - mean).abs();

            signals[i] = if z_score < -1.0 && spread >= self.min_spread {
                TradeSignal::Buy.into()
            } else if z_score > 1.0 && spread >= self.min_spread {
                TradeSignal::Sell.into()
            } else {
                TradeSignal::Hold.into()
            };
        }

        signals
    }

    /// Find momentum-based opportunities
    ///
    /// Generates signals based on price momentum over the window.
    pub fn find_momentum_signals(&self, prices: &[f64], window_size: usize) -> Vec<i32> {
        if prices.len() < window_size + 1 {
            return vec![0; prices.len()];
        }

        let mut signals = vec![0; prices.len()];

        for i in window_size..prices.len() {
            let momentum = prices[i] - prices[i - window_size];
            let momentum_pct = momentum / prices[i - window_size] * 100.0;

            signals[i] = if momentum_pct > 5.0 {
                // Strong upward momentum - consider selling
                TradeSignal::Sell.into()
            } else if momentum_pct < -5.0 {
                // Strong downward momentum - consider buying
                TradeSignal::Buy.into()
            } else {
                TradeSignal::Hold.into()
            };
        }

        signals
    }

    /// Backtest a trading strategy
    ///
    /// # Arguments
    /// * `prices` - Price series
    /// * `signals` - Trade signals (1 = buy, -1 = sell, 0 = hold)
    ///
    /// # Returns
    /// * Total profit/loss from the strategy
    pub fn backtest(&self, prices: &[f64], signals: &[i32]) -> f64 {
        if prices.len() != signals.len() {
            return 0.0;
        }

        let mut position = 0.0;
        let mut cash = 0.0;
        let mut entry_price = 0.0;

        for (i, (&price, &signal)) in prices.iter().zip(signals.iter()).enumerate() {
            match TradeSignal::from(signal) {
                TradeSignal::Buy if position <= 0.0 => {
                    // Close short position if any
                    if position < 0.0 {
                        cash += position * (entry_price - price);
                    }
                    // Open long position
                    position = self.max_position.min(100.0);
                    entry_price = price;
                }
                TradeSignal::Sell if position >= 0.0 => {
                    // Close long position if any
                    if position > 0.0 {
                        cash += position * (price - entry_price);
                    }
                    // Open short position
                    position = -self.max_position.min(100.0);
                    entry_price = price;
                }
                _ => {}
            }

            // Close position at end
            if i == prices.len() - 1 && position != 0.0 {
                if position > 0.0 {
                    cash += position * (price - entry_price);
                } else {
                    cash += -position * (entry_price - price);
                }
            }
        }

        cash
    }

    /// Calculate Sharpe ratio for a series of returns
    pub fn calculate_sharpe(&self, returns: &[f64], risk_free_rate: f64) -> f64 {
        if returns.is_empty() {
            return 0.0;
        }

        let mean_return: f64 = returns.iter().sum::<f64>() / returns.len() as f64;
        let excess_return = mean_return - risk_free_rate;

        let variance = returns
            .iter()
            .map(|r| (r - mean_return).powi(2))
            .sum::<f64>()
            / returns.len() as f64;

        let std = variance.sqrt();

        if std > 1e-6 {
            excess_return / std * (252_f64).sqrt() // Annualized
        } else {
            0.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mean_reversion_signals() {
        let optimizer = TradeOptimizer::new(5.0, 100.0);

        // Price series with clear mean-reversion opportunity
        let prices = vec![
            50.0, 50.0, 50.0, 50.0, 50.0, // Establish mean
            30.0, // Drop below mean -> buy signal
            70.0, // Rise above mean -> sell signal
        ];

        let signals = optimizer.find_opportunities(&prices, 5);

        // Should have buy signal at index 5 (price dropped)
        assert_eq!(signals[5], 1);
        // Should have sell signal at index 6 (price rose)
        assert_eq!(signals[6], -1);
    }

    #[test]
    fn test_backtest_profitable() {
        let optimizer = TradeOptimizer::new(5.0, 100.0);

        // Simple profitable scenario: buy low, sell high
        let prices = vec![100.0, 90.0, 110.0, 100.0];
        let signals = vec![0, 1, -1, 0]; // Buy at 90, sell at 110

        let profit = optimizer.backtest(&prices, &signals);

        // Profit = 100 units * (110 - 90) = 2000
        assert!(profit > 0.0);
    }

    #[test]
    fn test_short_window() {
        let optimizer = TradeOptimizer::new(5.0, 100.0);

        let prices = vec![50.0, 60.0];
        let signals = optimizer.find_opportunities(&prices, 5);

        // Window larger than data, should return all holds
        assert!(signals.iter().all(|&s| s == 0));
    }

    #[test]
    fn test_sharpe_ratio() {
        let optimizer = TradeOptimizer::new(5.0, 100.0);

        // Consistent positive returns
        let returns = vec![0.01, 0.02, 0.01, 0.015, 0.01];
        let sharpe = optimizer.calculate_sharpe(&returns, 0.0);

        // Should be positive for positive returns
        assert!(sharpe > 0.0);
    }
}
