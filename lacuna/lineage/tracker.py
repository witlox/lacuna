"""Lineage tracker for data flow and dependency tracking."""

from typing import Any, Optional

import networkx as nx
import structlog

from lacuna.config import get_settings
from lacuna.models.classification import Classification, DataTier
from lacuna.models.data_operation import DataOperation
from lacuna.models.lineage import LineageEdge, LineageGraph, LineageNode

logger = structlog.get_logger()


def get_lineage_backend() -> Any:
    """Get the appropriate lineage backend based on configuration."""
    settings = get_settings()

    # Use in-memory backend for development with SQLite
    if settings.database.url.startswith("sqlite"):
        from lacuna.lineage.memory_backend import InMemoryLineageBackend

        return InMemoryLineageBackend()
    else:
        from lacuna.lineage.backend import LineageBackend

        return LineageBackend()


class LineageTracker:
    """
    Track data lineage and dependencies using a graph structure.

    Features:
    - In-memory graph for fast traversal
    - Persistent storage for audit trail
    - Classification inheritance through lineage
    - Tag propagation tracking
    """

    def __init__(
        self,
        backend: Optional[Any] = None,
        enabled: bool = True,
        max_depth: int = 10,
    ):
        """Initialize lineage tracker.

        Args:
            backend: Storage backend for persistence
            enabled: Enable/disable lineage tracking
            max_depth: Maximum depth for traversal
        """
        settings = get_settings()
        self.enabled = enabled and settings.lineage.enabled
        self.max_depth = max_depth or settings.lineage.max_depth
        self._backend = backend or get_lineage_backend()

        # In-memory graph for fast traversal
        self._graph = nx.DiGraph()
        self._node_classifications: dict[str, Classification] = {}
        self._node_metadata: dict[str, dict[str, Any]] = {}

    def track_operation(
        self,
        operation: DataOperation,
        classification: Optional[Classification] = None,
    ) -> Optional[LineageEdge]:
        """Track a data operation as a lineage edge.

        Args:
            operation: Data operation to track
            classification: Classification of the destination

        Returns:
            Created lineage edge, or None if not applicable
        """
        if not self.enabled:
            return None

        # Create edges for transformations with sources
        if operation.sources and operation.destination:
            edges = []
            for source in operation.sources:
                edge = LineageEdge(
                    source_id=source,
                    destination_id=operation.destination,
                    operation_type=operation.operation_type.value,
                    operation_id=operation.operation_id,
                    user_id=operation.user.user_id if operation.user else None,
                    transformation_code=operation.code,
                    transformation_description=operation.transformation_type,
                    destination_classification=(
                        classification.tier.value if classification else None
                    ),
                    tags_propagated=classification.tags if classification else [],
                    metadata={
                        "purpose": operation.purpose,
                        "environment": operation.environment,
                        "project": operation.project,
                    },
                )

                self._add_edge_to_graph(edge)
                edges.append(edge)

            # Persist edges
            self._backend.write_edges(edges)

            logger.info(
                "lineage_tracked",
                sources=operation.sources,
                destination=operation.destination,
                operation=operation.operation_type.value,
                edge_count=len(edges),
            )

            return edges[0] if len(edges) == 1 else None

        # Single source/destination operations
        if operation.resource_id and operation.destination:
            edge = LineageEdge(
                source_id=operation.resource_id,
                destination_id=operation.destination,
                operation_type=operation.operation_type.value,
                operation_id=operation.operation_id,
                user_id=operation.user.user_id if operation.user else None,
                transformation_code=operation.code,
                destination_classification=(
                    classification.tier.value if classification else None
                ),
                tags_propagated=classification.tags if classification else [],
            )

            self._add_edge_to_graph(edge)
            self._backend.write_edge(edge)

            logger.info(
                "lineage_tracked",
                source=operation.resource_id,
                destination=operation.destination,
                operation=operation.operation_type.value,
            )

            return edge

        return None

    def _add_edge_to_graph(self, edge: LineageEdge) -> None:
        """Add an edge to the in-memory graph."""
        self._graph.add_edge(
            edge.source_id,
            edge.destination_id,
            edge_id=edge.edge_id,
            operation_type=edge.operation_type,
            timestamp=edge.timestamp,
            tags_propagated=edge.tags_propagated,
        )

    def get_upstream(
        self, artifact_id: str, max_depth: Optional[int] = None
    ) -> list[str]:
        """Get all upstream dependencies of an artifact.

        Args:
            artifact_id: Artifact to find dependencies for
            max_depth: Maximum depth to traverse

        Returns:
            List of upstream artifact IDs
        """
        depth = max_depth or self.max_depth

        # First check in-memory graph
        if artifact_id in self._graph:
            upstream = []
            for node in nx.ancestors(self._graph, artifact_id):
                # Check depth
                try:
                    path_length = nx.shortest_path_length(
                        self._graph, node, artifact_id
                    )
                    if path_length <= depth:
                        upstream.append(node)
                except nx.NetworkXNoPath:
                    continue
            if upstream:
                return upstream

        # Fall back to database
        edges = self._backend.get_upstream_edges(artifact_id, max_depth=depth)
        return list({edge.source_id for edge in edges})

    def get_downstream(
        self, artifact_id: str, max_depth: Optional[int] = None
    ) -> list[str]:
        """Get all downstream dependents of an artifact.

        Args:
            artifact_id: Artifact to find dependents for
            max_depth: Maximum depth to traverse

        Returns:
            List of downstream artifact IDs
        """
        depth = max_depth or self.max_depth

        # First check in-memory graph
        if artifact_id in self._graph:
            downstream = []
            for node in nx.descendants(self._graph, artifact_id):
                try:
                    path_length = nx.shortest_path_length(
                        self._graph, artifact_id, node
                    )
                    if path_length <= depth:
                        downstream.append(node)
                except nx.NetworkXNoPath:
                    continue
            if downstream:
                return downstream

        # Fall back to database
        edges = self._backend.get_downstream_edges(artifact_id, max_depth=depth)
        return list({edge.destination_id for edge in edges})

    def get_lineage(self, artifact_id: str) -> LineageGraph:
        """Get complete lineage graph for an artifact.

        Args:
            artifact_id: Artifact to get lineage for

        Returns:
            LineageGraph with all connected nodes and edges
        """
        graph = LineageGraph(name=f"lineage_{artifact_id}")

        # Add the target node
        cached_classification = self._node_classifications.get(artifact_id)
        classification_tier = (
            cached_classification.tier if cached_classification else None
        )
        graph.add_node(
            LineageNode(
                node_id=artifact_id,
                classification_tier=classification_tier,
            )
        )

        # Get upstream and downstream edges
        upstream_edges = self._backend.get_upstream_edges(
            artifact_id, max_depth=self.max_depth
        )
        downstream_edges = self._backend.get_downstream_edges(
            artifact_id, max_depth=self.max_depth
        )

        # Add all edges to graph
        for edge in upstream_edges + downstream_edges:
            graph.add_edge(edge)

        return graph

    def compute_inherited_classification(
        self,
        artifact_id: str,
        own_classification: Optional[Classification] = None,
    ) -> Classification:
        """Compute classification considering lineage inheritance.

        Classification rules:
        - Joins: Maximum classification of all sources
        - Aggregations: May downgrade if no individual PII
        - Filters: Inherit source classification
        - Transformations: Inherit unless explicitly anonymized

        Args:
            artifact_id: Artifact to compute classification for
            own_classification: The artifact's own classification

        Returns:
            Classification with inheritance applied
        """
        # Get upstream artifacts
        upstream = self.get_upstream(artifact_id, max_depth=1)

        if not upstream:
            # No parents - use own classification or default to PUBLIC
            return own_classification or Classification(
                tier=DataTier.PUBLIC,
                confidence=0.5,
                reasoning="No lineage - using default classification",
                classifier_name="LineageTracker",
            )

        # Collect parent classifications
        parent_tiers = []
        all_tags = set(own_classification.tags if own_classification else [])

        for parent_id in upstream:
            if parent_id in self._node_classifications:
                parent_class = self._node_classifications[parent_id]
                parent_tiers.append(parent_class.tier)
                all_tags.update(parent_class.tags)

        if not parent_tiers:
            return own_classification or Classification(
                tier=DataTier.PUBLIC,
                confidence=0.5,
                reasoning="No parent classifications found",
                classifier_name="LineageTracker",
            )

        # Inherit most restrictive tier
        inherited_tier = max(parent_tiers)

        # Own classification can upgrade but not downgrade
        if own_classification:
            inherited_tier = max(inherited_tier, own_classification.tier)

        reasoning = (
            f"Inherited {inherited_tier.value} from {len(parent_tiers)} parent(s). "
            f"Propagated tags: {', '.join(all_tags)}"
        )

        return Classification(
            tier=inherited_tier,
            confidence=0.95,  # High confidence for inheritance
            reasoning=reasoning,
            matched_rules=["lineage_inheritance"],
            tags=list(all_tags),
            classifier_name="LineageTracker",
            parent_classification_id=(
                own_classification.classification_id if own_classification else None
            ),
        )

    def register_classification(
        self, artifact_id: str, classification: Classification
    ) -> None:
        """Register a classification for an artifact.

        Args:
            artifact_id: Artifact ID
            classification: Classification to register
        """
        self._node_classifications[artifact_id] = classification
        self._graph.add_node(artifact_id, classification=classification.tier.value)

    def get_impact_analysis(self, artifact_id: str) -> dict[str, Any]:
        """Analyze impact of changes to an artifact.

        Args:
            artifact_id: Artifact to analyze

        Returns:
            Impact analysis with downstream dependencies
        """
        downstream = self.get_downstream(artifact_id)
        downstream_edges = self._backend.get_downstream_edges(artifact_id)

        # Group by depth
        depth_map: dict[int, list[str]] = {}
        for node in downstream:
            try:
                if node in self._graph and artifact_id in self._graph:
                    depth = nx.shortest_path_length(self._graph, artifact_id, node)
                else:
                    depth = 1  # Default depth
                if depth not in depth_map:
                    depth_map[depth] = []
                depth_map[depth].append(node)
            except nx.NetworkXNoPath:
                continue

        return {
            "artifact_id": artifact_id,
            "downstream_count": len(downstream),
            "downstream_artifacts": downstream,
            "by_depth": depth_map,
            "edge_count": len(downstream_edges),
        }

    def to_graph(self, artifact_id: Optional[str] = None) -> str:
        """Generate text representation of lineage graph.

        Args:
            artifact_id: Optional artifact to show lineage for

        Returns:
            Text tree representation
        """
        if artifact_id:
            graph = self.get_lineage(artifact_id)
            return self._graph_to_tree(graph, artifact_id)

        # Show entire graph
        lines = ["Lineage Graph:", f"  Nodes: {self._graph.number_of_nodes()}"]
        lines.append(f"  Edges: {self._graph.number_of_edges()}")

        return "\n".join(lines)

    def _graph_to_tree(
        self, graph: LineageGraph, root_id: str, prefix: str = ""
    ) -> str:
        """Convert lineage graph to tree representation."""
        lines = []
        node = graph.nodes.get(root_id)

        if node:
            tier_str = (
                f" ({node.classification_tier})" if node.classification_tier else ""
            )
            tags_str = f" [{', '.join(node.tags)}]" if node.tags else ""
            lines.append(f"{prefix}{root_id}{tier_str}{tags_str}")

        # Find upstream
        upstream = graph.get_upstream(root_id, max_depth=1)
        for i, parent_id in enumerate(upstream):
            is_last = i == len(upstream) - 1
            child_prefix = prefix + ("└─ " if is_last else "├─ ")
            lines.append(self._graph_to_tree(graph, parent_id, child_prefix))

        return "\n".join(lines)

    def clear_cache(self) -> None:
        """Clear in-memory graph cache."""
        self._graph.clear()
        self._node_classifications.clear()
        self._node_metadata.clear()
        logger.info("lineage_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get lineage tracker statistics."""
        return {
            "enabled": self.enabled,
            "max_depth": self.max_depth,
            "nodes_in_memory": self._graph.number_of_nodes(),
            "edges_in_memory": self._graph.number_of_edges(),
            "classifications_cached": len(self._node_classifications),
        }
