"""Shared pytest fixtures for integration testing with GCP emulators."""

import os
from collections.abc import Generator
from typing import Any

import pytest


def _set_emulator_env() -> None:
    """Set environment variables for GCP emulators."""
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8086")
    os.environ.setdefault("PUBSUB_EMULATOR_HOST", "localhost:8085")
    os.environ.setdefault("STORAGE_EMULATOR_HOST", "http://localhost:9000")
    os.environ.setdefault("GCP_PROJECT_ID", "moose-labs-local")
    os.environ.setdefault("ENVIRONMENT", "test")


# Set emulator environment on module load
_set_emulator_env()


@pytest.fixture(scope="session")
def emulator_env() -> dict[str, str]:
    """Return emulator environment configuration."""
    return {
        "FIRESTORE_EMULATOR_HOST": os.environ["FIRESTORE_EMULATOR_HOST"],
        "PUBSUB_EMULATOR_HOST": os.environ["PUBSUB_EMULATOR_HOST"],
        "STORAGE_EMULATOR_HOST": os.environ["STORAGE_EMULATOR_HOST"],
        "GCP_PROJECT_ID": os.environ["GCP_PROJECT_ID"],
    }


@pytest.fixture(scope="session")
def gcp_project_id() -> str:
    """Return the GCP project ID for testing."""
    return os.environ.get("GCP_PROJECT_ID", "moose-labs-local")


# =============================================================================
# Firestore fixtures
# =============================================================================


@pytest.fixture(scope="session")
def firestore_client() -> Generator[Any, None, None]:
    """Create a Firestore client connected to the emulator.

    Requires: google-cloud-firestore
    """
    try:
        from google.cloud import firestore
    except ImportError:
        pytest.skip("google-cloud-firestore not installed")

    client = firestore.Client(project=os.environ["GCP_PROJECT_ID"])
    yield client
    client.close()


@pytest.fixture
def clean_firestore(firestore_client: Any) -> Generator[Any, None, None]:
    """Provide a Firestore client and clean up all documents after test."""
    yield firestore_client

    # Clean up all collections after test
    for collection in firestore_client.collections():
        for doc in collection.stream():
            doc.reference.delete()


# =============================================================================
# PubSub fixtures
# =============================================================================


@pytest.fixture(scope="session")
def pubsub_publisher() -> Generator[Any, None, None]:
    """Create a PubSub publisher client connected to the emulator.

    Requires: google-cloud-pubsub
    """
    try:
        from google.cloud import pubsub_v1
    except ImportError:
        pytest.skip("google-cloud-pubsub not installed")

    publisher = pubsub_v1.PublisherClient()
    yield publisher


@pytest.fixture(scope="session")
def pubsub_subscriber() -> Generator[Any, None, None]:
    """Create a PubSub subscriber client connected to the emulator.

    Requires: google-cloud-pubsub
    """
    try:
        from google.cloud import pubsub_v1
    except ImportError:
        pytest.skip("google-cloud-pubsub not installed")

    subscriber = pubsub_v1.SubscriberClient()
    yield subscriber


@pytest.fixture
def pubsub_topic(
    pubsub_publisher: Any, gcp_project_id: str
) -> Generator[str, None, None]:
    """Create a temporary PubSub topic for testing."""
    import uuid

    topic_id = f"test-topic-{uuid.uuid4().hex[:8]}"
    topic_path = pubsub_publisher.topic_path(gcp_project_id, topic_id)

    pubsub_publisher.create_topic(request={"name": topic_path})
    yield topic_path

    # Cleanup
    pubsub_publisher.delete_topic(request={"topic": topic_path})


# =============================================================================
# Storage (MinIO) fixtures
# =============================================================================


@pytest.fixture(scope="session")
def minio_client() -> Generator[Any, None, None]:
    """Create a MinIO client for GCS-compatible storage testing.

    Requires: minio
    """
    try:
        from minio import Minio
    except ImportError:
        pytest.skip("minio not installed")

    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )
    yield client


@pytest.fixture
def test_bucket(minio_client: Any) -> Generator[str, None, None]:
    """Create a temporary bucket for testing."""
    import uuid

    bucket_name = f"test-bucket-{uuid.uuid4().hex[:8]}"

    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)

    yield bucket_name

    # Cleanup - remove all objects then bucket
    objects = minio_client.list_objects(bucket_name, recursive=True)
    for obj in objects:
        minio_client.remove_object(bucket_name, obj.object_name)
    minio_client.remove_bucket(bucket_name)


# =============================================================================
# Redis fixtures
# =============================================================================


@pytest.fixture(scope="session")
def redis_client() -> Generator[Any, None, None]:
    """Create a Redis client for testing.

    Requires: redis
    """
    try:
        import redis
    except ImportError:
        pytest.skip("redis not installed")

    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    yield client
    client.close()


@pytest.fixture
def clean_redis(redis_client: Any) -> Generator[Any, None, None]:
    """Provide a Redis client and flush DB after test."""
    yield redis_client
    redis_client.flushdb()


# =============================================================================
# PostgreSQL fixtures
# =============================================================================


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """Return PostgreSQL connection URL."""
    return "postgresql://moose:moose@localhost:5432/moose_labs"


@pytest.fixture(scope="session")
def postgres_connection(postgres_url: str) -> Generator[Any, None, None]:
    """Create a PostgreSQL connection for testing.

    Requires: psycopg2 or asyncpg
    """
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed")

    conn = psycopg2.connect(postgres_url)
    yield conn
    conn.close()
