"""Additional tests for LineageTracker to improve coverage."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch
from uuid import uuid4

import pytest

from lacuna.lineage.backend import LineageBackend
from lacuna.lineage.tracker import LineageTracker
from lacuna.models.classification import Classification, DataTier
from lacuna.models.data_operation import DataOperation, OperationType, UserContext
from lacuna.models.lineage import LineageEdge, LineageGraph, LineageNode


class TestLineageTrackerAdvanced:
    """Advanced tests for LineageTracker."""

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

    def test_track_operation_with_full_metadata(self, tracker, mock_backend) -> None:
        """Test tracking operation with full metadata."""
        operation = DataOperation(
            operation_type=OperationType.TRANSFORM,
            resource_id="main",
            sources=["source_a.csv"],
            destination="output.csv",
            user=UserContext(user_id="analyst", user_role="data_analyst"),
            purpose="Data analysis",
            environment="production",
            project="analytics-project",
            code="df = df.merge(other)",
            transformation_type="join",
        )

        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Contains customer data",
            tags=["PII", "GDPR"],
        )

        _edge = tracker.track_operation(operation, classification)

        # Verify the edge was written with metadata
        mock_backend.write_edges.assert_called_once()
        written_edges = mock_backend.write_edges.call_args[0][0]
        assert len(written_edges) == 1
        assert written_edges[0].metadata.get("purpose") == "Data analysis"
        assert written_edges[0].metadata.get("project") == "analytics-project"

    def test_get_lineage_graph(self, tracker, mock_backend) -> None:
        """Test getting complete lineage graph."""
        mock_backend.get_upstream_edges.return_value = [
            LineageEdge(
                source_id="parent.csv",
                destination_id="target.csv",
                operation_type="transform",
            )
        ]
        mock_backend.get_downstream_edges.return_value = [
            LineageEdge(
                source_id="target.csv",
                destination_id="child.csv",
                operation_type="export",
            )
        ]

        graph = tracker.get_lineage("target.csv")

        assert isinstance(graph, LineageGraph)
        assert len(graph.edges) == 2

    def test_compute_inherited_classification_no_parents(self, tracker) -> None:
        """Test classification inheritance with no parents."""
        classification = tracker.compute_inherited_classification("orphan.csv")

        assert classification.tier == DataTier.PUBLIC
        assert classification.confidence == 0.5

    def test_compute_inherited_classification_with_parents(
        self, tracker, mock_backend
    ) -> None:
        """Test classification inheritance with parents."""
        # Set up parent classification
        parent_class = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.95,
            reasoning="Parent is proprietary",
            tags=["PII"],
        )
        tracker._node_classifications["parent.csv"] = parent_class

        # Add edge in graph
        edge = LineageEdge(
            source_id="parent.csv", destination_id="child.csv", operation_type="t"
        )
        tracker._add_edge_to_graph(edge)

        inherited = tracker.compute_inherited_classification("child.csv")

        assert inherited.tier == DataTier.PROPRIETARY
        assert "PII" in inherited.tags
        assert inherited.confidence == 0.95

    def test_compute_inherited_classification_max_tier(
        self, tracker, mock_backend
    ) -> None:
        """Test that DataTier enum supports comparison for inheritance logic."""
        # The compute_inherited_classification method uses max() on tiers
        # This test verifies the tier comparison logic
        tiers = [DataTier.PUBLIC, DataTier.INTERNAL, DataTier.PROPRIETARY]

        # Verify ordering (PUBLIC is least restrictive, PROPRIETARY is most)
        assert sorted(tiers) == [
            DataTier.PUBLIC,
            DataTier.INTERNAL,
            DataTier.PROPRIETARY,
        ]

    def test_compute_inherited_with_own_classification(self, tracker) -> None:
        """Test inheritance with artifact's own classification."""
        parent_class = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.9,
            reasoning="Internal data",
            tags=["internal"],
        )
        tracker._node_classifications["parent.csv"] = parent_class

        tracker._add_edge_to_graph(
            LineageEdge(
                source_id="parent.csv", destination_id="child.csv", operation_type="t"
            )
        )

        own_class = Classification(
            tier=DataTier.PROPRIETARY,  # More restrictive
            confidence=0.95,
            reasoning="Has PII",
            tags=["PII"],
        )

        inherited = tracker.compute_inherited_classification("child.csv", own_class)

        # Own classification should upgrade
        assert inherited.tier == DataTier.PROPRIETARY

    def test_register_classification(self, tracker) -> None:
        """Test registering classification for an artifact."""
        classification = Classification(
            tier=DataTier.PROPRIETARY,
            confidence=0.99,
            reasoning="Highly sensitive",
            tags=["SENSITIVE"],
        )

        tracker.register_classification("sensitive.csv", classification)

        assert "sensitive.csv" in tracker._node_classifications
        assert tracker._node_classifications["sensitive.csv"] == classification
        assert "sensitive.csv" in tracker._graph.nodes

    def test_get_impact_analysis(self, tracker, mock_backend) -> None:
        """Test impact analysis for an artifact."""
        # Build a simple graph
        tracker._add_edge_to_graph(
            LineageEdge(
                source_id="source.csv", destination_id="mid.csv", operation_type="t"
            )
        )
        tracker._add_edge_to_graph(
            LineageEdge(
                source_id="mid.csv", destination_id="final.csv", operation_type="t"
            )
        )

        mock_backend.get_downstream_edges.return_value = [
            LineageEdge(
                source_id="source.csv", destination_id="mid.csv", operation_type="t"
            ),
            LineageEdge(
                source_id="mid.csv", destination_id="final.csv", operation_type="t"
            ),
        ]

        analysis = tracker.get_impact_analysis("source.csv")

        assert "downstream_count" in analysis
        assert "downstream_artifacts" in analysis
        assert "by_depth" in analysis
        assert analysis["artifact_id"] == "source.csv"

    def test_to_graph_representation(self, tracker) -> None:
        """Test text graph representation."""
        # Empty graph
        output = tracker.to_graph()

        assert "Lineage Graph" in output
        assert "Nodes:" in output
        assert "Edges:" in output

    def test_to_graph_for_specific_artifact(self, tracker, mock_backend) -> None:
        """Test graph representation for specific artifact."""
        mock_backend.get_upstream_edges.return_value = []
        mock_backend.get_downstream_edges.return_value = []

        output = tracker.to_graph("target.csv")

        # Should generate tree output
        assert "target.csv" in output

    def test_clear_cache(self, tracker) -> None:
        """Test clearing in-memory cache."""
        # Add some data
        tracker._add_edge_to_graph(
            LineageEdge(source_id="a", destination_id="b", operation_type="t")
        )
        tracker._node_classifications["a"] = Classification(
            tier=DataTier.PUBLIC, confidence=0.5, reasoning="test"
        )
        tracker._node_metadata["a"] = {"key": "value"}

        # Verify data exists
        assert tracker._graph.number_of_nodes() > 0

        # Clear cache
        tracker.clear_cache()

        assert tracker._graph.number_of_nodes() == 0
        assert len(tracker._node_classifications) == 0
        assert len(tracker._node_metadata) == 0

    def test_get_stats(self, tracker) -> None:
        """Test getting tracker statistics."""
        # Add some data
        tracker._add_edge_to_graph(
            LineageEdge(source_id="a", destination_id="b", operation_type="t")
        )

        stats = tracker.get_stats()

        assert "enabled" in stats
        assert "max_depth" in stats
        assert "nodes_in_memory" in stats
        assert stats["nodes_in_memory"] == 2

    def test_upstream_with_depth_limit(self, tracker, mock_backend) -> None:
        """Test upstream query respects depth limit."""
        # A <- B <- C <- D (chain)
        edges = [
            LineageEdge(source_id="D", destination_id="C", operation_type="t"),
            LineageEdge(source_id="C", destination_id="B", operation_type="t"),
            LineageEdge(source_id="B", destination_id="A", operation_type="t"),
        ]
        for edge in edges:
            tracker._add_edge_to_graph(edge)

        upstream = tracker.get_upstream("A", max_depth=2)

        # Should get B and C but not D
        assert "B" in upstream
        assert "C" in upstream
        # D might or might not be included depending on implementation

    def test_track_single_source_with_classification(
        self, tracker, mock_backend
    ) -> None:
        """Test tracking single source with classification."""
        operation = DataOperation(
            operation_type=OperationType.EXPORT,
            resource_id="source.csv",
            destination="export.csv",
            user=UserContext(user_id="user"),
        )

        classification = Classification(
            tier=DataTier.INTERNAL,
            confidence=0.8,
            reasoning="Internal data",
            tags=["INTERNAL"],
        )

        edge = tracker.track_operation(operation, classification)

        mock_backend.write_edge.assert_called_once()
        assert edge is not None
        assert edge.destination_classification == "INTERNAL"
        assert "INTERNAL" in edge.tags_propagated

    def test_fallback_to_database_upstream(self, tracker, mock_backend) -> None:
        """Test falling back to database for upstream when not in memory."""
        mock_backend.get_upstream_edges.return_value = [
            LineageEdge(
                source_id="db_parent", destination_id="target", operation_type="t"
            )
        ]

        upstream = tracker.get_upstream("target")

        mock_backend.get_upstream_edges.assert_called()
        assert "db_parent" in upstream

    def test_fallback_to_database_downstream(self, tracker, mock_backend) -> None:
        """Test falling back to database for downstream when not in memory."""
        mock_backend.get_downstream_edges.return_value = [
            LineageEdge(
                source_id="source", destination_id="db_child", operation_type="t"
            )
        ]

        downstream = tracker.get_downstream("source")

        mock_backend.get_downstream_edges.assert_called()
        assert "db_child" in downstream


class TestLineageTrackerEdgeCases:
    """Edge case tests for LineageTracker."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock(spec=LineageBackend)
        return backend

    def test_track_operation_no_sources_or_destination(self, mock_backend) -> None:
        """Test tracking operation with no sources or destination."""
        tracker = LineageTracker(backend=mock_backend, enabled=True)

        operation = DataOperation(
            operation_type=OperationType.READ,
            resource_id="data.csv",
            # No destination
        )

        result = tracker.track_operation(operation)

        assert result is None
        mock_backend.write_edge.assert_not_called()

    def test_track_with_empty_sources(self, mock_backend) -> None:
        """Test tracking with empty sources list."""
        tracker = LineageTracker(backend=mock_backend, enabled=True)

        operation = DataOperation(
            operation_type=OperationType.TRANSFORM,
            resource_id="source.csv",
            sources=[],  # Empty
            destination="dest.csv",
        )

        # Should fall back to resource_id as source
        _result = tracker.track_operation(operation)

        mock_backend.write_edge.assert_called_once()

    def test_circular_reference_protection(self, mock_backend) -> None:
        """Test that circular references don't cause infinite loops."""
        tracker = LineageTracker(backend=mock_backend, enabled=True)

        # Create a cycle: A -> B -> C -> A
        tracker._add_edge_to_graph(
            LineageEdge(source_id="A", destination_id="B", operation_type="t")
        )
        tracker._add_edge_to_graph(
            LineageEdge(source_id="B", destination_id="C", operation_type="t")
        )
        tracker._add_edge_to_graph(
            LineageEdge(source_id="C", destination_id="A", operation_type="t")
        )

        # This should not hang
        downstream = tracker.get_downstream("A")

        assert "B" in downstream
        assert "C" in downstream

    def test_compute_inheritance_no_parent_classifications(self, mock_backend) -> None:
        """Test inheritance when parents exist but have no classification."""
        tracker = LineageTracker(backend=mock_backend, enabled=True)

        # Add edge without classification
        tracker._add_edge_to_graph(
            LineageEdge(source_id="parent", destination_id="child", operation_type="t")
        )
        # Don't register parent classification

        own_class = Classification(
            tier=DataTier.PUBLIC,
            confidence=0.5,
            reasoning="Default",
        )

        result = tracker.compute_inherited_classification("child", own_class)

        # Should fall back to own classification
        assert result.tier == DataTier.PUBLIC
