//! Example Axum HTTP service for Moose Labs.

use std::net::SocketAddr;

use axum::{routing::get, Json, Router};
use serde::Serialize;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use shared::config::Settings;

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    version: String,
    environment: String,
}

#[derive(Serialize)]
struct RootResponse {
    message: String,
}

async fn health_check() -> Json<HealthResponse> {
    let settings = Settings::load();
    Json(HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        environment: settings.environment,
    })
}

async fn root() -> Json<RootResponse> {
    Json(RootResponse {
        message: "Welcome to Moose Labs Example Service".to_string(),
    })
}

fn app() -> Router {
    Router::new()
        .route("/", get(root))
        .route("/health", get(health_check))
        .layer(TraceLayer::new_for_http())
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "example_service=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    let settings = Settings::load();
    let addr: SocketAddr = format!("0.0.0.0:{}", settings.port).parse()?;

    tracing::info!("Starting server on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app()).await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_root() {
        let app = app();
        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_health_check() {
        let app = app();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/health")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }
}
