# syntax=docker/dockerfile:1

# =============================================================================
# Build stage: Compile the Rust binary
# =============================================================================
FROM rust:1.75-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy workspace files
COPY Cargo.toml Cargo.lock ./
COPY shared ./shared
COPY example-service ./example-service

# Build the release binary
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo build --release --package example-service && \
    cp /app/target/release/example-service /app/example-service-bin

# =============================================================================
# Runtime stage: Minimal image for production
# =============================================================================
FROM debian:bookworm-slim AS runtime

WORKDIR /app

# Install runtime dependencies and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash appuser

# Copy the binary from builder
COPY --from=builder /app/example-service-bin /app/example-service

# Set ownership and switch to non-root user
RUN chown appuser:appgroup /app/example-service
USER appuser

# Expose the application port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["/app/example-service"]
