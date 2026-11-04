# Moose Labs

Monorepo for experimental projects on GCP free tier.

## Prerequisites

- [Just](https://github.com/casey/just) - Task runner
- [uv](https://github.com/astral-sh/uv) - Python package manager
- [Rust](https://rustup.rs/) - Rust toolchain
- [Maturin](https://github.com/PyO3/maturin) - Rust+Python build tool (`pip install maturin`)
- [Docker](https://www.docker.com/) - Container runtime
- [OpenTofu](https://opentofu.org/) - Infrastructure as Code

## Quick Start

```bash
# Install dependencies
just setup

# Run tests
just test

# Start local GCP emulators
just emulators-up

# View all available commands
just --list
```

## Project Structure

```
moose-labs/
├── infra/                      # OpenTofu infrastructure
│   ├── modules/                # Reusable modules
│   │   ├── artifact-registry/  # Docker image registry
│   │   ├── cloud-run/          # Cloud Run services
│   │   └── networking/         # VPC and networking
│   └── environments/
│       ├── dev/                # Development environment
│       └── prod/               # Production environment
├── libs/                       # Hybrid Rust+Python libraries (Maturin)
│   └── trade-optimizer/        # Battery & trade optimization engine
├── services/
│   ├── python/                 # Python services (uv workspace)
│   │   ├── example-api/        # Example FastAPI service
│   │   └── shared/             # Shared Python utilities
│   └── rust/                   # Rust services (cargo workspace)
│       ├── example-service/    # Example Axum service
│       └── shared/             # Shared Rust utilities
├── testing/
│   ├── docker-compose.yml      # Local GCP emulators
│   ├── conftest.py             # Shared pytest fixtures
│   └── integration/            # Cross-service integration tests
└── justfile                    # Task runner commands
```

## Development

### Python Services

```bash
# Navigate to Python workspace
cd services/python

# Install dependencies
uv sync --all-packages

# Run tests
uv run pytest

# Run a specific service
uv run uvicorn example_api.main:app --reload

# Lint and format
uv run ruff check . && uv run ruff format .
```

### Rust Services

```bash
# Navigate to Rust workspace
cd services/rust

# Build all services
cargo build

# Run tests
cargo test

# Run a specific service
cargo run -p example-service

# Lint
cargo clippy && cargo fmt --check
```

### Local Testing with Emulators

```bash
# Start all emulators (Firestore, PubSub, MinIO, Redis, PostgreSQL)
just emulators-up

# Run integration tests
just test-integration

# Stop emulators
just emulators-down
```

Emulator endpoints when running locally:
- Firestore: `localhost:8086`
- PubSub: `localhost:8085`
- MinIO (GCS-compatible): `localhost:9000` (Console: `localhost:9001`)
- Redis: `localhost:6379`
- PostgreSQL: `localhost:5432`

## Infrastructure

### Initial Setup

1. Copy the example tfvars:
   ```bash
   cp infra/environments/dev/terraform.tfvars.example infra/environments/dev/terraform.tfvars
   ```

2. Edit with your GCP project ID:
   ```bash
   $EDITOR infra/environments/dev/terraform.tfvars
   ```

3. Initialize and apply:
   ```bash
   just infra-init dev
   just infra-plan dev
   just infra-apply dev
   ```

### Deploy Services

Images are automatically built and pushed via GitHub Actions on merge to main.

For manual deployment:
```bash
# Build Docker images
just docker-build

# Push to Artifact Registry (requires gcloud auth)
docker push <your-registry>/example-api:latest
```

## CI/CD

GitHub Actions workflows:
- **ci.yml**: Runs on PRs - linting and testing for Python, Rust, and OpenTofu
- **deploy.yml**: Runs on main - builds images and deploys infrastructure

### Required GitHub Secrets

For deployment workflows, configure these secrets:
- `GCP_PROJECT_ID`: Your GCP project ID
- `WIF_PROVIDER`: Workload Identity Federation provider
- `WIF_SERVICE_ACCOUNT`: Service account for deployments

## Hybrid Libraries (Rust + Python)

The `libs/` directory contains high-performance Rust libraries with Python bindings via [Maturin](https://github.com/PyO3/maturin) and [PyO3](https://pyo3.rs/).

### trade-optimizer

Battery storage and trading optimization engine. Rust core for performance, Python for orchestration.

```bash
# Build and install for development
just setup-libs

# Or manually
cd libs/trade-optimizer
maturin develop --release
```

Usage:
```python
from trade_optimizer import BatteryOptimizer, BatteryConfig
import numpy as np

config = BatteryConfig(capacity_mwh=100.0, max_charge_rate_mw=25.0, max_discharge_rate_mw=25.0)
optimizer = BatteryOptimizer(config)

prices = np.array([20, 25, 80, 95, 60, 30], dtype=np.float64)
schedule, revenue, final_soc = optimizer.optimize(prices, initial_soc=0.5)
```

### Adding a Hybrid Library

1. Create directory: `libs/my-library/`
2. Set up Maturin project with `Cargo.toml` and `pyproject.toml`
3. Implement Rust core with PyO3 bindings in `src/`
4. Add Python orchestration in `python/`
5. Update `justfile` commands for the new library

## Adding New Services

### Python Service

1. Create directory: `services/python/my-service/`
2. Add `pyproject.toml` with dependencies
3. Add to workspace: edit `services/python/pyproject.toml`
4. Create Dockerfile based on `example-api/Dockerfile`

### Rust Service

1. Create directory: `services/rust/my-service/`
2. Add `Cargo.toml` with workspace dependencies
3. Add to workspace: edit `services/rust/Cargo.toml`
4. Create Dockerfile based on `example-service/Dockerfile`

## License

MIT
