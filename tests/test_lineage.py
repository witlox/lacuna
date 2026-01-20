"""Tests for lineage tracking."""

import pytest

from lacuna.models.lineage import LineageEdge, LineageGraph, LineageNode


class TestLineageNode:
    """Tests for LineageNode model."""

    def test_node_creation(self) -> None:
        """Test creating a lineage node."""
        node = LineageNode(
            node_id="customers.csv",
            resource_type="file",
            classification_tier="PROPRIETARY",
            tags=["PII", "CUSTOMER_DATA"],
        )

        assert node.node_id == "customers.csv"
        assert node.classification_tier == "PROPRIETARY"
        assert "PII" in node.tags

    def test_node_to_dict(self) -> None:
        """Test node serialization."""
        node = LineageNode(
            node_id="data.csv",
            resource_type="file",
        )

        data = node.to_dict()

        assert data["node_id"] == "data.csv"
        assert data["resource_type"] == "file"


class TestLineageEdge:
    """Tests for LineageEdge model."""

    def test_edge_creation(self) -> None:
        """Test creating a lineage edge."""
        edge = LineageEdge(
            source_id="source.csv",
            destination_id="target.csv",
            operation_type="transform",
        )

        assert edge.source_id == "source.csv"
        assert edge.destination_id == "target.csv"
        assert edge.operation_type == "transform"

    def test_edge_with_classification(self) -> None:
        """Test edge with classification propagation."""
        edge = LineageEdge(
            source_id="customers.csv",
            destination_id="analysis.csv",
            operation_type="join",
            source_classification="PROPRIETARY",
            destination_classification="PROPRIETARY",
            tags_propagated=["PII", "CUSTOMER_DATA"],
        )

        assert edge.source_classification == "PROPRIETARY"
        assert "PII" in edge.tags_propagated


class TestLineageGraph:
    """Tests for LineageGraph model."""

    def test_graph_creation(self) -> None:
        """Test creating an empty graph."""
        graph = LineageGraph(name="test-graph")

        assert graph.name == "test-graph"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self) -> None:
        """Test adding nodes to graph."""
        graph = LineageGraph()

        node = LineageNode(node_id="test.csv")
        graph.add_node(node)

        assert "test.csv" in graph.nodes
        assert graph.get_node_count() == 1

    def test_add_edge(self) -> None:
        """Test adding edges to graph."""
        graph = LineageGraph()

        edge = LineageEdge(
            source_id="source.csv",
            destination_id="target.csv",
            operation_type="copy",
        )
        graph.add_edge(edge)

        # Should auto-create nodes
        assert "source.csv" in graph.nodes
        assert "target.csv" in graph.nodes
        assert graph.get_edge_count() == 1

    def test_get_upstream(self) -> None:
        """Test getting upstream dependencies."""
        graph = LineageGraph()

        # A -> B -> C
        graph.add_edge(
            LineageEdge(source_id="A", destination_id="B", operation_type="t")
        )
        graph.add_edge(
            LineageEdge(source_id="B", destination_id="C", operation_type="t")
        )

        upstream = graph.get_upstream("C")

        assert "A" in upstream
        assert "B" in upstream
        assert len(upstream) == 2

    def test_get_downstream(self) -> None:
        """Test getting downstream dependencies."""
        graph = LineageGraph()

        # A -> B, A -> C
        graph.add_edge(
            LineageEdge(source_id="A", destination_id="B", operation_type="t")
        )
        graph.add_edge(
            LineageEdge(source_id="A", destination_id="C", operation_type="t")
        )

        downstream = graph.get_downstream("A")

        assert "B" in downstream
        assert "C" in downstream
        assert len(downstream) == 2

    def test_max_depth_limit(self) -> None:
        """Test depth limiting in traversal."""
        graph = LineageGraph()

        # A -> B -> C -> D
        graph.add_edge(
            LineageEdge(source_id="A", destination_id="B", operation_type="t")
        )
        graph.add_edge(
            LineageEdge(source_id="B", destination_id="C", operation_type="t")
        )
        graph.add_edge(
            LineageEdge(source_id="C", destination_id="D", operation_type="t")
        )

        # With max_depth=1, should only get C
        upstream = graph.get_upstream("D", max_depth=1)

        assert "C" in upstream
        assert "A" not in upstream  # Too deep

    def test_lineage_chain(self) -> None:
        """Test getting lineage chains."""
        graph = LineageGraph()

        # Root A and B both feed into C
        graph.add_edge(
            LineageEdge(source_id="A", destination_id="C", operation_type="t")
        )
        graph.add_edge(
            LineageEdge(source_id="B", destination_id="C", operation_type="t")
        )

        chains = graph.get_lineage_chain("C")

        # Should have paths from both roots
        assert len(chains) >= 1

    def test_to_graphviz(self) -> None:
        """Test GraphViz output generation."""
        graph = LineageGraph()

        graph.add_edge(
            LineageEdge(source_id="A", destination_id="B", operation_type="join")
        )

        dot = graph.to_graphviz()

        assert "digraph" in dot
        assert '"A"' in dot
        assert '"B"' in dot
        assert "join" in dot
