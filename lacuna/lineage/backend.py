"""Lineage storage backend for PostgreSQL."""

from datetime import datetime
from typing import Any, Optional

import structlog
from sqlalchemy import desc

from lacuna.db.base import session_scope
from lacuna.db.models import LineageEdgeModel
from lacuna.models.lineage import LineageEdge

logger = structlog.get_logger()


class LineageBackend:
    """
    PostgreSQL backend for lineage edge storage.

    Stores lineage edges and provides query capabilities
    for upstream/downstream traversal.
    """

    def write_edge(self, edge: LineageEdge) -> None:
        """Write a lineage edge to storage.

        Args:
            edge: Lineage edge to store
        """
        with session_scope() as session:
            model = LineageEdgeModel(
                id=edge.edge_id,
                timestamp=edge.timestamp,
                source_artifact_id=edge.source_id,
                target_artifact_id=edge.destination_id,
                operation_type=edge.operation_type,
                extra_data={
                    "user_id": edge.user_id,
                    "transformation_code": edge.transformation_code,
                    "transformation_description": edge.transformation_description,
                    "source_classification": edge.source_classification,
                    "destination_classification": edge.destination_classification,
                    "tags_propagated": edge.tags_propagated,
                    **edge.metadata,
                },
            )
            session.add(model)

            logger.debug(
                "lineage_edge_written",
                source=edge.source_id,
                destination=edge.destination_id,
                operation=edge.operation_type,
            )

    def write_edges(self, edges: list[LineageEdge]) -> None:
        """Write multiple lineage edges in a batch.

        Args:
            edges: List of lineage edges to store
        """
        if not edges:
            return

        with session_scope() as session:
            for edge in edges:
                model = LineageEdgeModel(
                    id=edge.edge_id,
                    timestamp=edge.timestamp,
                    source_artifact_id=edge.source_id,
                    target_artifact_id=edge.destination_id,
                    operation_type=edge.operation_type,
                    extra_data={
                        "user_id": edge.user_id,
                        "transformation_code": edge.transformation_code,
                        "transformation_description": edge.transformation_description,
                        "source_classification": edge.source_classification,
                        "destination_classification": edge.destination_classification,
                        "tags_propagated": edge.tags_propagated,
                        **edge.metadata,
                    },
                )
                session.add(model)

            logger.info("lineage_batch_written", count=len(edges))

    def get_upstream_edges(
        self, artifact_id: str, max_depth: Optional[int] = None
    ) -> list[LineageEdge]:
        """Get all upstream edges for an artifact.

        Args:
            artifact_id: Target artifact ID
            max_depth: Maximum depth to traverse

        Returns:
            List of upstream lineage edges
        """
        with session_scope() as session:
            edges = []
            visited = set()
            queue = [(artifact_id, 0)]

            while queue:
                current_id, depth = queue.pop(0)

                if current_id in visited:
                    continue

                if max_depth is not None and depth > max_depth:
                    continue

                visited.add(current_id)

                # Find edges where current_id is target
                results = (
                    session.query(LineageEdgeModel)
                    .filter(LineageEdgeModel.target_artifact_id == current_id)
                    .all()
                )

                for model in results:
                    edge = self._model_to_edge(model)
                    edges.append(edge)
                    queue.append((model.source_artifact_id, depth + 1))

            return edges

    def get_downstream_edges(
        self, artifact_id: str, max_depth: Optional[int] = None
    ) -> list[LineageEdge]:
        """Get all downstream edges for an artifact.

        Args:
            artifact_id: Source artifact ID
            max_depth: Maximum depth to traverse

        Returns:
            List of downstream lineage edges
        """
        with session_scope() as session:
            edges = []
            visited = set()
            queue = [(artifact_id, 0)]

            while queue:
                current_id, depth = queue.pop(0)

                if current_id in visited:
                    continue

                if max_depth is not None and depth > max_depth:
                    continue

                visited.add(current_id)

                # Find edges where current_id is source
                results = (
                    session.query(LineageEdgeModel)
                    .filter(LineageEdgeModel.source_artifact_id == current_id)
                    .all()
                )

                for model in results:
                    edge = self._model_to_edge(model)
                    edges.append(edge)
                    queue.append((model.target_artifact_id, depth + 1))

            return edges

    def get_edges_for_artifact(self, artifact_id: str) -> list[LineageEdge]:
        """Get all edges connected to an artifact.

        Args:
            artifact_id: Artifact ID

        Returns:
            List of connected lineage edges
        """
        with session_scope() as session:
            results = (
                session.query(LineageEdgeModel)
                .filter(
                    (LineageEdgeModel.source_artifact_id == artifact_id)
                    | (LineageEdgeModel.target_artifact_id == artifact_id)
                )
                .order_by(desc(LineageEdgeModel.timestamp))
                .all()
            )

            return [self._model_to_edge(model) for model in results]

    def get_recent_edges(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[LineageEdge]:
        """Get recent lineage edges.

        Args:
            limit: Maximum number of edges
            since: Only edges after this time

        Returns:
            List of recent lineage edges
        """
        with session_scope() as session:
            q = session.query(LineageEdgeModel)

            if since:
                q = q.filter(LineageEdgeModel.timestamp >= since)

            results = q.order_by(desc(LineageEdgeModel.timestamp)).limit(limit).all()

            return [self._model_to_edge(model) for model in results]

    def _model_to_edge(self, model: LineageEdgeModel) -> LineageEdge:
        """Convert database model to LineageEdge."""
        extra_data: dict[str, Any] = dict(model.extra_data) if model.extra_data else {}
        return LineageEdge(
            edge_id=model.id,
            timestamp=model.timestamp,
            source_id=model.source_artifact_id,
            destination_id=model.target_artifact_id,
            operation_type=model.operation_type,
            user_id=extra_data.get("user_id"),
            transformation_code=extra_data.get("transformation_code"),
            transformation_description=extra_data.get("transformation_description"),
            source_classification=extra_data.get("source_classification"),
            destination_classification=extra_data.get("destination_classification"),
            tags_propagated=extra_data.get("tags_propagated", []),
            metadata={
                k: v
                for k, v in extra_data.items()
                if k
                not in (
                    "user_id",
                    "transformation_code",
                    "transformation_description",
                    "source_classification",
                    "destination_classification",
                    "tags_propagated",
                )
            },
        )
