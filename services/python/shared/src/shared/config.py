"""Shared configuration management."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    debug: bool = False

    # GCP Configuration
    gcp_project_id: str = ""

    # Service Configuration
    service_name: str = "moose-labs"
    log_level: str = "INFO"

    # Emulator endpoints (for local development)
    firestore_emulator_host: str = ""
    pubsub_emulator_host: str = ""
    storage_emulator_host: str = ""

    @property
    def is_emulated(self) -> bool:
        """Check if running against emulators."""
        return bool(
            self.firestore_emulator_host
            or self.pubsub_emulator_host
            or self.storage_emulator_host
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
