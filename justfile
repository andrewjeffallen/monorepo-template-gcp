# Moose Labs Monorepo Justfile
# Run `just --list` to see all available commands

set shell := ["bash", "-uc"]

# Default recipe - show help
default:
    @just --list

# =============================================================================
# Development Setup
# =============================================================================

# Install all dependencies (Python + Rust)
setup: setup-python setup-rust
    @echo "Setup complete!"

# Install Python dependencies
setup-python:
    cd services/python && uv sync --all-packages

# Install Rust dependencies (check they compile)
setup-rust:
    cd services/rust && cargo build

# =============================================================================
# Testing
# =============================================================================

# Run all tests
test: test-python test-rust

# Run Python tests
test-python *args:
    cd services/python && uv run pytest {{args}}

# Run Rust tests
test-rust *args:
    cd services/rust && cargo test {{args}}

# Run tests with coverage (Python)
test-python-cov:
    cd services/python && uv run pytest --cov --cov-report=html

# =============================================================================
# Linting & Formatting
# =============================================================================

# Lint and format all code
lint: lint-python lint-rust

# Lint Python code
lint-python:
    cd services/python && uv run ruff check . && uv run ruff format --check .

# Format Python code
fmt-python:
    cd services/python && uv run ruff format . && uv run ruff check --fix .

# Lint Rust code
lint-rust:
    cd services/rust && cargo clippy -- -D warnings && cargo fmt --check

# Format Rust code
fmt-rust:
    cd services/rust && cargo fmt

# Format all code
fmt: fmt-python fmt-rust

# =============================================================================
# Building
# =============================================================================

# Build all services
build: build-python build-rust

# Build Python packages
build-python:
    cd services/python && uv build --all

# Build Rust binaries (release)
build-rust:
    cd services/rust && cargo build --release

# =============================================================================
# Docker
# =============================================================================

# Build all Docker images
docker-build: docker-build-python docker-build-rust

# Build Python service Docker images
docker-build-python service="example-api":
    docker build -t moose-labs/{{service}}:latest services/python/{{service}}

# Build Rust service Docker images
docker-build-rust service="example-service":
    docker build -t moose-labs/{{service}}:latest services/rust/{{service}}

# =============================================================================
# Local Development Environment
# =============================================================================

# Start local GCP emulators
emulators-up:
    docker compose -f testing/docker-compose.yml up -d

# Stop local GCP emulators
emulators-down:
    docker compose -f testing/docker-compose.yml down

# View emulator logs
emulators-logs:
    docker compose -f testing/docker-compose.yml logs -f

# Run integration tests (starts emulators if needed)
test-integration: emulators-up
    cd services/python && uv run pytest testing/integration -v
    @just emulators-down

# =============================================================================
# Infrastructure (OpenTofu)
# =============================================================================

# Initialize OpenTofu for an environment
infra-init env="dev":
    cd infra/environments/{{env}} && tofu init

# Plan infrastructure changes
infra-plan env="dev":
    cd infra/environments/{{env}} && tofu plan

# Apply infrastructure changes
infra-apply env="dev":
    cd infra/environments/{{env}} && tofu apply

# Destroy infrastructure (use with caution!)
infra-destroy env="dev":
    cd infra/environments/{{env}} && tofu destroy

# =============================================================================
# CI Helpers
# =============================================================================

# Run all CI checks (lint + test)
ci: lint test
    @echo "All CI checks passed!"

# Clean build artifacts
clean:
    cd services/rust && cargo clean
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
