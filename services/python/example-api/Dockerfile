# syntax=docker/dockerfile:1

# =============================================================================
# Build stage: Install dependencies using uv
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Copy workspace configuration
COPY pyproject.toml ./
COPY shared ./shared
COPY example-api ./example-api

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package example-api

# =============================================================================
# Runtime stage: Minimal image for production
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash appuser

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set up the environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "example_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
