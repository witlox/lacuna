"""In-memory lineage storage backend for development."""

from datetime import datetime
from typing import Optional

import structlog

from lacuna.models.lineage import LineageEdge

logger = structlog.get_logger()


class InMemoryLineageBackend:
    """
    In-memory backend for lineage tracking during development.

    Stores lineage edges in memory - data is lost on restart.
    This is suitable for local development and testing only.
    """

    def __init__(self) -> None:
        """Initialize in-memory lineage backend."""
        self._edges: list[LineageEdge] = []

    def write_edge(self, edge: LineageEdge) -> None:
        """Write a lineage edge to storage.

        Args:
            edge: Lineage edge to store
        """
        self._edges.append(edge)

        logger.debug(
            "lineage_edge_written_memory",
            source=edge.source_id,
            destination=edge.destination_id,
            operation=edge.operation_type,
        )

    def write_edges(self, edges: list[LineageEdge]) -> None:
        """Write multiple lineage edges in a batch.

        Args:
            edges: List of lineage edges to store
        """
        for edge in edges:
            self.write_edge(edge)

    def get_upstream(
        self,
        artifact_id: str,
        max_depth: int = 10,
    ) -> list[LineageEdge]:
        """Get upstream edges (inputs to this artifact).

        Args:
            artifact_id: Artifact to find upstream for
            max_depth: Maximum depth to traverse

        Returns:
            List of upstream edges
        """
        result: list[LineageEdge] = []
        visited: set[str] = set()
        queue = [(artifact_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth or current_id in visited:
                continue

            visited.add(current_id)

            for edge in self._edges:
                if edge.destination_id == current_id:
                    result.append(edge)
                    queue.append((edge.source_id, depth + 1))

        return result

    def get_downstream(
        self,
        artifact_id: str,
        max_depth: int = 10,
    ) -> list[LineageEdge]:
        """Get downstream edges (outputs from this artifact).

        Args:
            artifact_id: Artifact to find downstream for
            max_depth: Maximum depth to traverse

        Returns:
            List of downstream edges
        """
        result: list[LineageEdge] = []
        visited: set[str] = set()
        queue = [(artifact_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth or current_id in visited:
                continue

            visited.add(current_id)

            for edge in self._edges:
                if edge.source_id == current_id:
                    result.append(edge)
                    queue.append((edge.destination_id, depth + 1))

        return result

    def get_edges_for_artifact(self, artifact_id: str) -> list[LineageEdge]:
        """Get all edges involving an artifact.

        Args:
            artifact_id: Artifact ID to search for

        Returns:
            List of edges involving the artifact
        """
        return [
            e
            for e in self._edges
            if e.source_id == artifact_id or e.destination_id == artifact_id
        ]

    def query(
        self,
        source_id: Optional[str] = None,
        destination_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[LineageEdge]:
        """Query lineage edges.

        Args:
            source_id: Filter by source artifact
            destination_id: Filter by destination artifact
            operation_type: Filter by operation type
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum results to return

        Returns:
            List of matching edges
        """
        results = self._edges.copy()

        if source_id:
            results = [e for e in results if e.source_id == source_id]

        if destination_id:
            results = [e for e in results if e.destination_id == destination_id]

        if operation_type:
            results = [e for e in results if e.operation_type == operation_type]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        # Sort by timestamp descending
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[:limit]

    def clear(self) -> None:
        """Clear all edges (for testing)."""
        self._edges.clear()
