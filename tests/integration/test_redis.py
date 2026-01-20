"""Integration tests for Redis caching."""

import json
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.integration


class TestRedisConnection:
    """Tests for Redis connectivity."""

    def test_redis_connection(self, redis_client):
        """Test that we can connect to Redis."""
        assert redis_client.ping() is True

    def test_redis_set_get(self, redis_client):
        """Test basic set/get operations."""
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        assert value.decode() == "test_value"


class TestClassificationCache:
    """Tests for classification result caching."""

    def test_cache_classification_result(self, redis_client):
        """Test caching a classification result."""
        cache_key = "classification:test_query_hash"
        classification_data = {
            "tier": "PROPRIETARY",
            "confidence": 0.95,
            "reasoning": "Contains customer data",
            "tags": ["PII", "GDPR"],
            "classifier_name": "heuristic",
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

        redis_client.setex(
            cache_key, 3600, json.dumps(classification_data)  # 1 hour TTL
        )

        # Retrieve and verify
        cached = redis_client.get(cache_key)
        assert cached is not None

        result = json.loads(cached)
        assert result["tier"] == "PROPRIETARY"
        assert result["confidence"] == 0.95

    def test_cache_expiration(self, redis_client):
        """Test that cache entries expire."""
        cache_key = "classification:expiring_key"

        redis_client.setex(cache_key, 1, "temporary_value")  # 1 second TTL

        # Should exist immediately
        assert redis_client.get(cache_key) is not None

        # Wait for expiration
        import time

        time.sleep(1.5)

        # Should be gone
        assert redis_client.get(cache_key) is None

    def test_cache_batch_operations(self, redis_client):
        """Test batch caching operations."""
        # Create multiple cache entries
        pipe = redis_client.pipeline()

        for i in range(10):
            key = f"classification:batch_{i}"
            value = json.dumps({"tier": "PUBLIC", "index": i})
            pipe.setex(key, 3600, value)

        pipe.execute()

        # Verify all were cached
        for i in range(10):
            cached = redis_client.get(f"classification:batch_{i}")
            assert cached is not None
            data = json.loads(cached)
            assert data["index"] == i


class TestPolicyCache:
    """Tests for policy decision caching."""

    def test_cache_policy_decision(self, redis_client):
        """Test caching a policy decision."""
        cache_key = "policy:decision:export:proprietary:downloads"
        decision_data = {
            "allowed": False,
            "reasoning": "Cannot export PROPRIETARY data to unmanaged location",
            "alternatives": [
                "Use anonymized version",
                "Save to governed location",
            ],
            "policy_id": "export-policy-001",
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

        redis_client.setex(cache_key, 300, json.dumps(decision_data))  # 5 min TTL

        # Retrieve and verify
        cached = redis_client.get(cache_key)
        result = json.loads(cached)

        assert result["allowed"] is False
        assert len(result["alternatives"]) == 2

    def test_invalidate_policy_cache(self, redis_client):
        """Test invalidating policy cache entries."""
        # Create policy cache entries
        for i in range(5):
            redis_client.setex(f"policy:v1:rule_{i}", 3600, f"value_{i}")

        # Invalidate by pattern (simulate policy update)
        keys = redis_client.keys("policy:v1:*")
        if keys:
            redis_client.delete(*keys)

        # Verify all are gone
        for i in range(5):
            assert redis_client.get(f"policy:v1:rule_{i}") is None


class TestLineageCache:
    """Tests for lineage graph caching."""

    def test_cache_lineage_subgraph(self, redis_client):
        """Test caching a lineage subgraph."""
        cache_key = "lineage:upstream:customers.csv"
        lineage_data = {
            "root": "customers.csv",
            "nodes": [
                {"id": "customers.csv", "tier": "PROPRIETARY"},
                {"id": "raw.customer_master", "tier": "PROPRIETARY"},
                {"id": "salesforce.contacts", "tier": "PROPRIETARY"},
            ],
            "edges": [
                {"source": "raw.customer_master", "target": "customers.csv"},
                {"source": "salesforce.contacts", "target": "raw.customer_master"},
            ],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        redis_client.setex(cache_key, 600, json.dumps(lineage_data))  # 10 min TTL

        # Retrieve and verify
        cached = redis_client.get(cache_key)
        result = json.loads(cached)

        assert result["root"] == "customers.csv"
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2

    def test_cache_downstream_impact(self, redis_client):
        """Test caching downstream impact analysis."""
        cache_key = "lineage:downstream:source_table"
        impact_data = {
            "source": "source_table",
            "affected_count": 15,
            "affected_artifacts": [
                "derived_table_1",
                "report_1.csv",
                "dashboard_data",
            ],
            "max_depth": 3,
        }

        redis_client.setex(cache_key, 300, json.dumps(impact_data))

        cached = redis_client.get(cache_key)
        result = json.loads(cached)

        assert result["affected_count"] == 15
        assert len(result["affected_artifacts"]) == 3


class TestRateLimiting:
    """Tests for Redis-based rate limiting."""

    def test_sliding_window_rate_limit(self, redis_client):
        """Test sliding window rate limiting."""
        user_id = "test_user_ratelimit"
        window_key = f"ratelimit:{user_id}:classify"
        limit = 10
        window_seconds = 60

        # Simulate requests
        for _i in range(limit):
            current_count = redis_client.incr(window_key)
            if current_count == 1:
                redis_client.expire(window_key, window_seconds)

            # Should be allowed
            assert current_count <= limit

        # Next request should exceed limit
        current_count = redis_client.incr(window_key)
        assert current_count > limit

    def test_rate_limit_reset(self, redis_client):
        """Test that rate limit resets after window."""
        user_id = "test_user_reset"
        window_key = f"ratelimit:{user_id}:test"

        # Set a short-lived rate limit
        redis_client.setex(window_key, 1, "5")  # 1 second TTL

        import time

        time.sleep(1.5)

        # Should be reset
        assert redis_client.get(window_key) is None
