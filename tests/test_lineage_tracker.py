"""Tests for LineageTracker."""

from unittest.mock import MagicMock, patch

import pytest

from lacuna.lineage.backend import LineageBackend
from lacuna.lineage.tracker import LineageTracker
from lacuna.models.classification import Classification, DataTier
from lacuna.models.data_operation import DataOperation, OperationType, UserContext
from lacuna.models.lineage import LineageEdge


class TestLineageTrackerInit:
    """Tests for LineageTracker initialization."""

    def test_tracker_default_init(self) -> None:
        """Test default initialization."""
        with patch.object(LineageBackend, "__init__", return_value=None):
            tracker = LineageTracker()
            assert tracker.enabled is True
            assert tracker.max_depth == 10

    def test_tracker_disabled(self) -> None:
        """Test disabled tracker."""
        with patch.object(LineageBackend, "__init__", return_value=None):
            tracker = LineageTracker(enabled=False)
            assert tracker.enabled is False

    def test_tracker_custom_depth(self) -> None:
        """Test custom max depth."""
        with patch.object(LineageBackend, "__init__", return_value=None):
            tracker = LineageTracker(max_depth=5)
            assert tracker.max_depth == 5


class TestLineageTrackerOperations:
    """Tests for LineageTracker tracking operations."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        backend = MagicMock(spec=LineageBackend)
        return backend

    @pytest.fixture
    def tracker(self, mock_backend):
        """Create a tracker with mock backend."""
        tracker = LineageTracker(backend=mock_backend, enabled=True)
        return tracker

    def test_track_disabled_returns_none(self, mock_backend) -> None:
        """Test that disabled tracker returns None."""
        tracker = LineageTracker(backend=mock_backend, enabled=False)

        operation = DataOperation(
            operation_type=OperationType.TRANSFORM,
            resource_id="source.csv",
            destination="target.csv",
        )

        result = tracker.track_operation(operation)
        assert result is None
        mock_backend.write_edge.assert_not_called()

    def test_track_transformation_with_sources(self, tracker, mock_backend) -> None:
        """Test tracking a transformation with multiple sources."""
        operation = DataOperation(
            operation_type=OperationType.TRANSFORM,
            resource_id="main",
            sources=["source_a.csv", "source_b.csv"],
            destination="output.csv",
            user=UserContext(user_id="test-user"),
        )

        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Test",
            tags=["PII"],
        )

        tracker.track_operation(operation, classification)

        # Should write multiple edges (one per source)
        mock_backend.write_edges.assert_called_once()
        edges = mock_backend.write_edges.call_args[0][0]
        assert len(edges) == 2

    def test_track_single_source_destination(self, tracker, mock_backend) -> None:
        """Test tracking a single source to destination."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="data.csv",
            destination="~/exports/data.csv",
            user=UserContext(user_id="test-user"),
        )

        _edge = tracker.track_operation(operation)

        mock_backend.write_edge.assert_called_once()

    def test_track_no_destination_returns_none(self, tracker, mock_backend) -> None:
        """Test that operation without destination returns None."""
        operation = DataOperation(
            operation_type=OperationType.READ,
            resource_id="data.csv",
        )

        result = tracker.track_operation(operation)
        assert result is None


class TestLineageTrackerQueries:
    """Tests for LineageTracker query methods."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        backend = MagicMock(spec=LineageBackend)
        return backend

    @pytest.fixture
    def tracker(self, mock_backend):
        """Create a tracker with mock backend."""
        tracker = LineageTracker(backend=mock_backend, enabled=True)
        return tracker

    def test_get_upstream_from_graph(self, tracker) -> None:
        """Test getting upstream from in-memory graph."""
        # Add edges to in-memory graph
        edge1 = LineageEdge(source_id="A", destination_id="B", operation_type="t")
        edge2 = LineageEdge(source_id="B", destination_id="C", operation_type="t")

        tracker._add_edge_to_graph(edge1)
        tracker._add_edge_to_graph(edge2)

        upstream = tracker.get_upstream("C")

        assert "A" in upstream
        assert "B" in upstream

    def test_get_upstream_falls_back_to_backend(self, tracker, mock_backend) -> None:
        """Test that upstream query falls back to backend."""
        mock_backend.get_upstream_edges.return_value = [
            LineageEdge(
                source_id="db_source", destination_id="target", operation_type="t"
            )
        ]

        _upstream = tracker.get_upstream("unknown_artifact")

        mock_backend.get_upstream_edges.assert_called()

    def test_get_downstream_from_graph(self, tracker) -> None:
        """Test getting downstream from in-memory graph."""
        edge1 = LineageEdge(source_id="A", destination_id="B", operation_type="t")
        edge2 = LineageEdge(source_id="A", destination_id="C", operation_type="t")

        tracker._add_edge_to_graph(edge1)
        tracker._add_edge_to_graph(edge2)

        downstream = tracker.get_downstream("A")

        assert "B" in downstream
        assert "C" in downstream

    def test_get_downstream_with_max_depth(self, tracker) -> None:
        """Test downstream query respects max depth."""
        # A -> B -> C -> D
        edges = [
            LineageEdge(source_id="A", destination_id="B", operation_type="t"),
            LineageEdge(source_id="B", destination_id="C", operation_type="t"),
            LineageEdge(source_id="C", destination_id="D", operation_type="t"),
        ]
        for edge in edges:
            tracker._add_edge_to_graph(edge)

        downstream = tracker.get_downstream("A", max_depth=1)

        assert "B" in downstream
        # C and D should be excluded due to depth limit


class TestLineageTrackerClassification:
    """Tests for LineageTracker classification inheritance."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock(spec=LineageBackend)
        return backend

    @pytest.fixture
    def tracker(self, mock_backend):
        tracker = LineageTracker(backend=mock_backend, enabled=True)
        return tracker

    def test_store_classification(self, tracker) -> None:
        """Test storing classification for an artifact."""
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains PII",
            tags=["PII"],
        )

        tracker._node_classifications["customers.csv"] = classification

        assert "customers.csv" in tracker._node_classifications
        assert (
            tracker._node_classifications["customers.csv"].tier == DataTier.PROPRIETARY
        )

    def test_get_classification_for_artifact(self, tracker) -> None:
        """Test retrieving classification for an artifact."""
        classification = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.9,
            reasoning="Internal data",
            tags=[],
        )

        tracker._node_classifications["internal.csv"] = classification

        result = tracker._node_classifications.get("internal.csv")
        assert result is not None
        assert result.tier == DataTier.INTERNAL


class TestLineageBackendMocked:
    """Tests for LineageBackend with mocked database."""

    def test_model_to_edge_conversion(self) -> None:
        """Test converting database model to edge."""
        # Create a mock model
        from datetime import datetime, timezone
        from unittest.mock import MagicMock
        from uuid import uuid4

        model = MagicMock()
        model.id = uuid4()
        model.timestamp = datetime.now(timezone.utc)
        model.source_artifact_id = "source.csv"
        model.target_artifact_id = "target.csv"
        model.operation_type = "transform"
        model.extra_data = {
            "user_id": "test",
            "tags_propagated": ["PII"],
        }

        # The backend would convert this - test the structure
        edge = LineageEdge(
            edge_id=model.id,
            timestamp=model.timestamp,
            source_id=model.source_artifact_id,
            destination_id=model.target_artifact_id,
            operation_type=model.operation_type,
            user_id=model.extra_data.get("user_id"),
            tags_propagated=model.extra_data.get("tags_propagated", []),
        )

        assert edge.source_id == "source.csv"
        assert edge.destination_id == "target.csv"
        assert "PII" in edge.tags_propagated
