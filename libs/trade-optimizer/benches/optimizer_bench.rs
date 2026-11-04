//! Benchmarks for the trade optimizer

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use trade_optimizer::{BatteryConfig, BatteryOptimizer, TradeOptimizer};

fn generate_prices(n: usize) -> Vec<f64> {
    // Deterministic pseudo-random prices
    let mut prices = Vec::with_capacity(n);
    let mut val = 50.0;
    for i in 0..n {
        // Sinusoidal pattern with noise
        val = 50.0 + 30.0 * ((i as f64) * 0.1).sin() + ((i as f64) * 0.3).cos() * 10.0;
        prices.push(val.max(10.0));
    }
    prices
}

fn benchmark_battery_optimizer(c: &mut Criterion) {
    let config = BatteryConfig {
        capacity_mwh: 100.0,
        max_charge_rate_mw: 25.0,
        max_discharge_rate_mw: 25.0,
        efficiency: 0.9,
        min_soc: 0.1,
        max_soc: 0.9,
    };
    let optimizer = BatteryOptimizer::new(config);

    let mut group = c.benchmark_group("battery_optimizer");

    for size in [24, 168, 720, 8760].iter() {
        let prices = generate_prices(*size);

        group.bench_with_input(
            BenchmarkId::new("optimize", size),
            &prices,
            |b, prices| {
                b.iter(|| {
                    optimizer.optimize(black_box(prices), black_box(0.5)).unwrap()
                });
            },
        );
    }

    group.finish();
}

fn benchmark_trade_optimizer(c: &mut Criterion) {
    let optimizer = TradeOptimizer::new(5.0, 100.0);

    let mut group = c.benchmark_group("trade_optimizer");

    for size in [100, 1000, 10000].iter() {
        let prices = generate_prices(*size);

        group.bench_with_input(
            BenchmarkId::new("find_opportunities", size),
            &prices,
            |b, prices| {
                b.iter(|| {
                    optimizer.find_opportunities(black_box(prices), black_box(24))
                });
            },
        );
    }

    group.finish();
}

criterion_group!(benches, benchmark_battery_optimizer, benchmark_trade_optimizer);
criterion_main!(benches);
