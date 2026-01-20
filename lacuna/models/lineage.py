"""Lineage models for tracking data flow and dependencies."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


def _utc_now() -> datetime:
    """Get current UTC time in a timezone-aware manner."""
    return datetime.now(timezone.utc)


@dataclass
class LineageEdge:
    """
    Represents an edge in the lineage graph (source -> destination).

    Each edge captures a single data flow relationship, including
    the operation that created it and relevant metadata.
    """

    # Edge identification
    edge_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utc_now)

    # Source and destination
    source_id: str = ""
    destination_id: str = ""

    # Operation details
    operation_type: str = "unknown"  # read, write, join, transform, etc.
    operation_id: Optional[UUID] = None

    # User who performed the operation
    user_id: Optional[str] = None

    # Transformation details
    transformation_code: Optional[str] = None
    transformation_description: Optional[str] = None

    # Classification inheritance
    source_classification: Optional[str] = None  # PROPRIETARY/INTERNAL/PUBLIC
    destination_classification: Optional[str] = None

    # Tags propagated through this edge
    tags_propagated: list[str] = field(default_factory=list)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "edge_id": str(self.edge_id),
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "destination_id": self.destination_id,
            "operation_type": self.operation_type,
            "operation_id": str(self.operation_id) if self.operation_id else None,
            "user_id": self.user_id,
            "transformation_code": self.transformation_code,
            "transformation_description": self.transformation_description,
            "source_classification": self.source_classification,
            "destination_classification": self.destination_classification,
            "tags_propagated": self.tags_propagated,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageEdge":
        """Create from dictionary representation."""
        return cls(
            edge_id=UUID(data["edge_id"]) if "edge_id" in data else uuid4(),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else _utc_now()
            ),
            source_id=data.get("source_id", ""),
            destination_id=data.get("destination_id", ""),
            operation_type=data.get("operation_type", "unknown"),
            operation_id=(
                UUID(data["operation_id"]) if data.get("operation_id") else None
            ),
            user_id=data.get("user_id"),
            transformation_code=data.get("transformation_code"),
            transformation_description=data.get("transformation_description"),
            source_classification=data.get("source_classification"),
            destination_classification=data.get("destination_classification"),
            tags_propagated=data.get("tags_propagated", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LineageNode:
    """
    Represents a node in the lineage graph (a data resource).

    Each node represents a data resource with its metadata and classification.
    """

    # Node identification
    node_id: str  # Resource identifier
    resource_type: str = "unknown"  # file, table, dataset, query result
    resource_path: Optional[str] = None

    # Classification
    classification_tier: Optional[str] = None
    classification_confidence: Optional[float] = None
    tags: list[str] = field(default_factory=list)

    # Creation metadata
    created_at: datetime = field(default_factory=_utc_now)
    created_by: Optional[str] = None
    created_via: Optional[str] = None  # Operation type that created this

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "node_id": self.node_id,
            "resource_type": self.resource_type,
            "resource_path": self.resource_path,
            "classification_tier": self.classification_tier,
            "classification_confidence": self.classification_confidence,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "created_via": self.created_via,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageNode":
        """Create from dictionary representation."""
        return cls(
            node_id=data["node_id"],
            resource_type=data.get("resource_type", "unknown"),
            resource_path=data.get("resource_path"),
            classification_tier=data.get("classification_tier"),
            classification_confidence=data.get("classification_confidence"),
            tags=data.get("tags", []),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else _utc_now()
            ),
            created_by=data.get("created_by"),
            created_via=data.get("created_via"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LineageGraph:
    """
    Represents a complete lineage graph with nodes and edges.

    This is a directed acyclic graph (DAG) where nodes are data resources
    and edges represent data flow relationships.
    """

    # Graph identification
    graph_id: UUID = field(default_factory=uuid4)
    name: Optional[str] = None
    description: Optional[str] = None

    # Graph structure
    nodes: dict[str, LineageNode] = field(default_factory=dict)
    edges: list[LineageEdge] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def add_node(self, node: LineageNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.node_id] = node
        self.updated_at = _utc_now()

    def add_edge(self, edge: LineageEdge) -> None:
        """Add an edge to the graph."""
        # Ensure both nodes exist
        if edge.source_id not in self.nodes:
            self.add_node(LineageNode(node_id=edge.source_id))
        if edge.destination_id not in self.nodes:
            self.add_node(LineageNode(node_id=edge.destination_id))

        self.edges.append(edge)
        self.updated_at = _utc_now()

    def get_upstream(self, node_id: str, max_depth: Optional[int] = None) -> list[str]:
        """
        Get all upstream dependencies of a node.

        Args:
            node_id: The node to find upstream dependencies for
            max_depth: Maximum depth to traverse (None for unlimited)

        Returns:
            List of node IDs that are upstream dependencies
        """
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited:
                continue

            if max_depth is not None and depth > max_depth:
                continue

            visited.add(current_id)

            # Find all edges where current_id is the destination
            for edge in self.edges:
                if edge.destination_id == current_id:
                    queue.append((edge.source_id, depth + 1))

        # Remove the original node
        visited.discard(node_id)
        return list(visited)

    def get_downstream(
        self, node_id: str, max_depth: Optional[int] = None
    ) -> list[str]:
        """
        Get all downstream dependencies of a node.

        Args:
            node_id: The node to find downstream dependencies for
            max_depth: Maximum depth to traverse (None for unlimited)

        Returns:
            List of node IDs that are downstream dependencies
        """
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited:
                continue

            if max_depth is not None and depth > max_depth:
                continue

            visited.add(current_id)

            # Find all edges where current_id is the source
            for edge in self.edges:
                if edge.source_id == current_id:
                    queue.append((edge.destination_id, depth + 1))

        # Remove the original node
        visited.discard(node_id)
        return list(visited)

    def get_lineage_chain(self, node_id: str) -> list[list[str]]:
        """
        Get all lineage paths from root nodes to the specified node.

        Args:
            node_id: The node to get lineage chains for

        Returns:
            List of paths (each path is a list of node IDs)
        """
        # Find all root nodes (nodes with no incoming edges)
        nodes_with_incoming = {edge.destination_id for edge in self.edges}
        root_nodes = [
            nid for nid in self.nodes.keys() if nid not in nodes_with_incoming
        ]

        # Find all paths from each root to target
        all_paths: list[list[str]] = []

        def find_paths(current: str, target: str, path: list[str]) -> None:
            """DFS to find all paths from current to target."""
            if current == target:
                all_paths.append(path + [current])
                return

            if current in path:  # Cycle detection
                return

            # Find outgoing edges
            for edge in self.edges:
                if edge.source_id == current:
                    find_paths(edge.destination_id, target, path + [current])

        # Search from each root
        for root in root_nodes:
            find_paths(root, node_id, [])

        return all_paths

    def get_edges_for_node(self, node_id: str) -> list[LineageEdge]:
        """Get all edges connected to a node (incoming and outgoing)."""
        return [
            edge
            for edge in self.edges
            if edge.source_id == node_id or edge.destination_id == node_id
        ]

    def get_node_count(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self.nodes)

    def get_edge_count(self) -> int:
        """Get the number of edges in the graph."""
        return len(self.edges)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "graph_id": str(self.graph_id),
            "name": self.name,
            "description": self.description,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageGraph":
        """Create from dictionary representation."""
        graph = cls(
            graph_id=UUID(data["graph_id"]) if "graph_id" in data else uuid4(),
            name=data.get("name"),
            description=data.get("description"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else _utc_now()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else _utc_now()
            ),
        )

        # Add nodes
        nodes_data = data.get("nodes", {})
        for node_data in nodes_data.values():
            graph.add_node(LineageNode.from_dict(node_data))

        # Add edges
        edges_data = data.get("edges", [])
        for edge_data in edges_data:
            graph.edges.append(LineageEdge.from_dict(edge_data))

        return graph

    def to_graphviz(self) -> str:
        """
        Generate a GraphViz DOT representation of the lineage graph.

        Returns:
            DOT format string for visualization
        """
        lines = ["digraph lineage {", "  rankdir=LR;"]

        # Add nodes
        for node_id, node in self.nodes.items():
            label = node_id
            if node.classification_tier:
                label += f"\\n{node.classification_tier}"
            if node.tags:
                label += f"\\n{', '.join(node.tags)}"

            lines.append(f'  "{node_id}" [label="{label}"];')

        # Add edges
        for edge in self.edges:
            label = edge.operation_type
            if edge.transformation_description:
                label += f"\\n{edge.transformation_description}"

            lines.append(
                f'  "{edge.source_id}" -> "{edge.destination_id}" [label="{label}"];'
            )

        lines.append("}")
        return "\n".join(lines)
