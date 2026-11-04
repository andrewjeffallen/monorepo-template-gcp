//! Configuration management for Moose Labs services.

use config::{Config, Environment};
use serde::Deserialize;

/// Application settings loaded from environment variables.
#[derive(Debug, Deserialize)]
pub struct Settings {
    /// Current environment (development, staging, production)
    #[serde(default = "default_environment")]
    pub environment: String,

    /// Port to listen on
    #[serde(default = "default_port")]
    pub port: u16,

    /// GCP project ID
    #[serde(default)]
    pub gcp_project_id: String,

    /// Service name for logging/tracing
    #[serde(default = "default_service_name")]
    pub service_name: String,

    /// Log level (TRACE, DEBUG, INFO, WARN, ERROR)
    #[serde(default = "default_log_level")]
    pub log_level: String,

    /// Firestore emulator host (for local development)
    #[serde(default)]
    pub firestore_emulator_host: String,

    /// PubSub emulator host (for local development)
    #[serde(default)]
    pub pubsub_emulator_host: String,
}

fn default_environment() -> String {
    "development".to_string()
}

fn default_port() -> u16 {
    8080
}

fn default_service_name() -> String {
    "moose-labs".to_string()
}

fn default_log_level() -> String {
    "INFO".to_string()
}

impl Settings {
    /// Load settings from environment variables.
    ///
    /// Environment variables are expected to be uppercase with underscores,
    /// e.g., `GCP_PROJECT_ID`, `LOG_LEVEL`.
    #[must_use]
    pub fn load() -> Self {
        Config::builder()
            .add_source(Environment::default().separator("_"))
            .build()
            .expect("Failed to build configuration")
            .try_deserialize()
            .expect("Failed to deserialize configuration")
    }

    /// Check if running against emulators.
    #[must_use]
    pub fn is_emulated(&self) -> bool {
        !self.firestore_emulator_host.is_empty() || !self.pubsub_emulator_host.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_settings() {
        let settings = Settings::load();
        assert_eq!(settings.environment, "development");
        assert_eq!(settings.port, 8080);
    }
}
