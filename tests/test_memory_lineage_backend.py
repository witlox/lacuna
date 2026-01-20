"""Tests for in-memory lineage backend (dev mode)."""

from datetime import datetime, timedelta, timezone

import pytest

from lacuna.lineage.memory_backend import InMemoryLineageBackend
from lacuna.models.lineage import LineageEdge


class TestInMemoryLineageBackendInit:
    """Tests for InMemoryLineageBackend initialization."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        backend = InMemoryLineageBackend()
        assert backend._edges == []


class TestInMemoryLineageBackendWrite:
    """Tests for InMemoryLineageBackend write operations."""

    @pytest.fixture
    def backend(self) -> InMemoryLineageBackend:
        """Create a fresh backend for each test."""
        return InMemoryLineageBackend()

    @pytest.fixture
    def sample_edge(self) -> LineageEdge:
        """Create a sample lineage edge."""
        return LineageEdge(
            source_id="source.csv",
            destination_id="target.csv",
            operation_type="transform",
        )

    def test_write_single_edge(
        self, backend: InMemoryLineageBackend, sample_edge: LineageEdge
    ) -> None:
        """Test writing a single edge."""
        backend.write_edge(sample_edge)

        assert len(backend._edges) == 1
        assert backend._edges[0] == sample_edge

    def test_write_multiple_edges(self, backend: InMemoryLineageBackend) -> None:
        """Test writing multiple edges sequentially."""
        edges = [
            LineageEdge(
                source_id=f"source{i}.csv",
                destination_id="target.csv",
                operation_type="transform",
            )
            for i in range(3)
        ]

        for edge in edges:
            backend.write_edge(edge)

        assert len(backend._edges) == 3

    def test_write_edges_batch(self, backend: InMemoryLineageBackend) -> None:
        """Test batch writing edges."""
        edges = [
            LineageEdge(
                source_id=f"source{i}.csv",
                destination_id="target.csv",
                operation_type="join",
            )
            for i in range(5)
        ]

        backend.write_edges(edges)

        assert len(backend._edges) == 5


class TestInMemoryLineageBackendUpstream:
    """Tests for InMemoryLineageBackend upstream queries."""

    @pytest.fixture
    def backend_with_chain(self) -> InMemoryLineageBackend:
        """Create a backend with a linear chain: A -> B -> C -> D."""
        backend = InMemoryLineageBackend()
        backend.write_edge(
            LineageEdge(source_id="A", destination_id="B", operation_type="t")
        )
        backend.write_edge(
            LineageEdge(source_id="B", destination_id="C", operation_type="t")
        )
        backend.write_edge(
            LineageEdge(source_id="C", destination_id="D", operation_type="t")
        )
        return backend

    def test_get_upstream_single_level(
        self, backend_with_chain: InMemoryLineageBackend
    ) -> None:
        """Test getting immediate upstream."""
        edges = backend_with_chain.get_upstream("B", max_depth=1)

        assert len(edges) == 1
        assert edges[0].source_id == "A"

    def test_get_upstream_full_chain(
        self, backend_with_chain: InMemoryLineageBackend
    ) -> None:
        """Test getting full upstream chain."""
        edges = backend_with_chain.get_upstream("D", max_depth=10)

        # Should find C, B, A
        source_ids = [e.source_id for e in edges]
        assert "A" in source_ids
        assert "B" in source_ids
        assert "C" in source_ids

    def test_get_upstream_no_ancestors(
        self, backend_with_chain: InMemoryLineageBackend
    ) -> None:
        """Test getting upstream for root node."""
        edges = backend_with_chain.get_upstream("A")

        assert len(edges) == 0

    def test_get_upstream_respects_max_depth(
        self, backend_with_chain: InMemoryLineageBackend
    ) -> None:
        """Test that max_depth limits traversal."""
        edges = backend_with_chain.get_upstream("D", max_depth=2)

        # Should only find C and B, not A
        source_ids = [e.source_id for e in edges]
        assert "C" in source_ids
        assert "B" in source_ids
        # A should be excluded due to depth limit


class TestInMemoryLineageBackendDownstream:
    """Tests for InMemoryLineageBackend downstream queries."""

    @pytest.fixture
    def backend_with_tree(self) -> InMemoryLineageBackend:
        """Create a backend with a tree structure.

        A -> B -> D
        A -> C -> E
        """
        backend = InMemoryLineageBackend()
        backend.write_edge(
            LineageEdge(source_id="A", destination_id="B", operation_type="t")
        )
        backend.write_edge(
            LineageEdge(source_id="A", destination_id="C", operation_type="t")
        )
        backend.write_edge(
            LineageEdge(source_id="B", destination_id="D", operation_type="t")
        )
        backend.write_edge(
            LineageEdge(source_id="C", destination_id="E", operation_type="t")
        )
        return backend

    def test_get_downstream_single_level(
        self, backend_with_tree: InMemoryLineageBackend
    ) -> None:
        """Test getting immediate downstream."""
        edges = backend_with_tree.get_downstream("A", max_depth=1)

        assert len(edges) == 2
        destinations = {e.destination_id for e in edges}
        assert "B" in destinations
        assert "C" in destinations

    def test_get_downstream_full_tree(
        self, backend_with_tree: InMemoryLineageBackend
    ) -> None:
        """Test getting full downstream tree."""
        edges = backend_with_tree.get_downstream("A", max_depth=10)

        # Should find B, C, D, E
        destinations = {e.destination_id for e in edges}
        assert "B" in destinations
        assert "C" in destinations
        assert "D" in destinations
        assert "E" in destinations

    def test_get_downstream_no_descendants(
        self, backend_with_tree: InMemoryLineageBackend
    ) -> None:
        """Test getting downstream for leaf node."""
        edges = backend_with_tree.get_downstream("D")

        assert len(edges) == 0


class TestInMemoryLineageBackendQuery:
    """Tests for InMemoryLineageBackend query operations."""

    @pytest.fixture
    def backend_with_data(self) -> InMemoryLineageBackend:
        """Create a backend with sample data."""
        backend = InMemoryLineageBackend()

        now = datetime.now(timezone.utc)
        edges = [
            LineageEdge(
                source_id="source1.csv",
                destination_id="target.csv",
                operation_type="transform",
                timestamp=now - timedelta(hours=2),
            ),
            LineageEdge(
                source_id="source2.csv",
                destination_id="target.csv",
                operation_type="join",
                timestamp=now - timedelta(hours=1),
            ),
            LineageEdge(
                source_id="target.csv",
                destination_id="export.csv",
                operation_type="export",
                timestamp=now,
            ),
        ]

        for edge in edges:
            backend.write_edge(edge)

        return backend

    def test_query_all(self, backend_with_data: InMemoryLineageBackend) -> None:
        """Test querying all edges."""
        results = backend_with_data.query()

        assert len(results) == 3

    def test_query_by_source(self, backend_with_data: InMemoryLineageBackend) -> None:
        """Test querying by source ID."""
        results = backend_with_data.query(source_id="source1.csv")

        assert len(results) == 1
        assert results[0].source_id == "source1.csv"

    def test_query_by_destination(
        self, backend_with_data: InMemoryLineageBackend
    ) -> None:
        """Test querying by destination ID."""
        results = backend_with_data.query(destination_id="target.csv")

        assert len(results) == 2
        assert all(r.destination_id == "target.csv" for r in results)

    def test_query_by_operation_type(
        self, backend_with_data: InMemoryLineageBackend
    ) -> None:
        """Test querying by operation type."""
        results = backend_with_data.query(operation_type="export")

        assert len(results) == 1
        assert results[0].operation_type == "export"

    def test_query_with_limit(self, backend_with_data: InMemoryLineageBackend) -> None:
        """Test querying with limit."""
        results = backend_with_data.query(limit=2)

        assert len(results) == 2

    def test_query_sorted_by_timestamp(
        self, backend_with_data: InMemoryLineageBackend
    ) -> None:
        """Test that results are sorted by timestamp descending."""
        results = backend_with_data.query()

        for i in range(len(results) - 1):
            assert results[i].timestamp >= results[i + 1].timestamp

    def test_get_edges_for_artifact(
        self, backend_with_data: InMemoryLineageBackend
    ) -> None:
        """Test getting all edges for an artifact."""
        results = backend_with_data.get_edges_for_artifact("target.csv")

        # target.csv is source in one edge and destination in two
        assert len(results) == 3

    def test_clear(self, backend_with_data: InMemoryLineageBackend) -> None:
        """Test clearing all edges."""
        assert len(backend_with_data._edges) == 3

        backend_with_data.clear()

        assert len(backend_with_data._edges) == 0
