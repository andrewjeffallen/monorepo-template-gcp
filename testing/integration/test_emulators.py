"""Smoke tests to verify emulators are running correctly."""

import pytest


class TestEmulatorConnectivity:
    """Test that emulators are accessible."""

    def test_firestore_connection(self, firestore_client):
        """Test Firestore emulator is accessible."""
        # Write a test document
        doc_ref = firestore_client.collection("test").document("smoke-test")
        doc_ref.set({"status": "ok"})

        # Read it back
        doc = doc_ref.get()
        assert doc.exists
        assert doc.to_dict()["status"] == "ok"

        # Cleanup
        doc_ref.delete()

    def test_pubsub_topic_creation(self, pubsub_topic):
        """Test PubSub emulator allows topic creation."""
        assert pubsub_topic is not None
        assert "test-topic" in pubsub_topic

    def test_minio_bucket_creation(self, test_bucket, minio_client):
        """Test MinIO storage emulator is accessible."""
        assert minio_client.bucket_exists(test_bucket)

    def test_redis_connection(self, redis_client):
        """Test Redis is accessible."""
        redis_client.set("test-key", "test-value")
        assert redis_client.get("test-key") == "test-value"
        redis_client.delete("test-key")

    @pytest.mark.skip(reason="PostgreSQL fixture requires psycopg2")
    def test_postgres_connection(self, postgres_connection):
        """Test PostgreSQL is accessible."""
        cursor = postgres_connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
        cursor.close()
