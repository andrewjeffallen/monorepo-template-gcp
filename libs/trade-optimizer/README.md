# Trade Optimizer

High-performance battery and trade optimization engine with Python bindings.

**Rust for the heavy lifting, Python for the orchestration.**

## Features

- **Battery Optimizer**: Optimal dispatch scheduling for energy storage arbitrage
- **Trade Optimizer**: Mean-reversion and momentum-based trading signals
- **High Performance**: Core algorithms in Rust, 10-100x faster than pure Python
- **Python Integration**: Seamless NumPy array handling via PyO3
- **Orchestration Layer**: Data engineering utilities with pandas/polars support

## Installation

### From source (development)

```bash
# Install maturin
pip install maturin

# Build and install in development mode
cd libs/trade-optimizer
maturin develop --release

# Or use just
just setup-libs
```

### From wheel (production)

```bash
pip install trade-optimizer
```

## Quick Start

```python
import numpy as np
from trade_optimizer import BatteryOptimizer, BatteryConfig

# Configure battery (100 MWh, 25 MW charge/discharge)
config = BatteryConfig(
    capacity_mwh=100.0,
    max_charge_rate_mw=25.0,
    max_discharge_rate_mw=25.0,
    efficiency=0.9,
)

# Create optimizer
optimizer = BatteryOptimizer(config)

# Price forecast ($/MWh) - 24 hours
prices = np.array([
    20, 22, 18, 15, 18, 25,  # Night (low)
    45, 65, 85, 95, 90, 85,  # Morning peak
    80, 75, 70, 65, 70, 80,  # Afternoon
    95, 85, 60, 45, 30, 22,  # Evening peak then decline
], dtype=np.float64)

# Optimize dispatch schedule
schedule, revenue, final_soc = optimizer.optimize(prices, initial_soc=0.5)

print(f"Total Revenue: ${revenue:,.2f}")
print(f"Final SOC: {final_soc*100:.1f}%")
```

## Using the Orchestration Layer

```python
from trade_optimizer import BatteryConfig
from trade_optimizer.orchestration import OptimizationPipeline, ResultExporter

# Create pipeline
pipeline = OptimizationPipeline(
    battery_config=BatteryConfig(100.0, 25.0, 25.0)
)

# Run optimization
results = pipeline.run(prices, initial_soc=0.5)

# Analyze
analysis = pipeline.analyze_results(results)
print(f"Spread captured: ${analysis['price_spread_captured']:.2f}/MWh")

# Export
exporter = ResultExporter(output_dir="output")
exporter.to_parquet(results)
print(exporter.summary_report(results, analysis))
```

## Architecture

```
trade-optimizer/
├── src/                    # Rust source (PyO3 bindings)
│   ├── lib.rs             # Module entry, Python exports
│   ├── battery.rs         # Battery optimization algorithms
│   ├── trade.rs           # Trading signal generation
│   └── types.rs           # Shared types
├── python/
│   └── trade_optimizer/   # Python package
│       ├── __init__.py    # Re-exports Rust + Python
│       └── orchestration.py  # Data engineering layer
├── tests/                 # Python tests
├── benches/               # Rust benchmarks
├── Cargo.toml             # Rust dependencies
└── pyproject.toml         # Python/Maturin config
```

## Development

```bash
# Run Rust tests
cargo test

# Run Python tests
maturin develop && pytest tests -v

# Run benchmarks
cargo bench

# Lint
cargo clippy && cargo fmt --check
ruff check python && ruff format --check python
```

## Performance

Benchmarks on M1 MacBook Pro:

| Operation | Data Size | Time |
|-----------|-----------|------|
| Battery optimize | 24 periods | 15μs |
| Battery optimize | 8760 periods (1 year) | 2ms |
| Find arbitrage | 10000 periods | 500μs |

## License

MIT
