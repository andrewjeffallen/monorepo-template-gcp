"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from shared.config import get_settings


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    settings = get_settings()
    app.state.settings = settings
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Example API",
    description="Example FastAPI service for Moose Labs",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to Moose Labs Example API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
