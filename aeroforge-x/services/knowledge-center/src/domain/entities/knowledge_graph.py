from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .knowledge_node import KnowledgeNode
from .knowledge_link import KnowledgeLink


@dataclass
class KnowledgeGraph:
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: int = 1
    status: str = "draft"
    node_count: int = 0
    link_count: int = 0
    metadata: dict = field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _nodes: dict[str, KnowledgeNode] = field(default_factory=dict, repr=False)
    _links: dict[str, KnowledgeLink] = field(default_factory=dict, repr=False)

    def add_node(self, node: KnowledgeNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"Node {node.node_id} already exists in graph")
        self._nodes[node.node_id] = node
        self.node_count = len(self._nodes)
        self.updated_at = datetime.now(timezone.utc)

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found in graph")
        links_to_remove = [
            lid for lid, link in self._links.items()
            if link.source_node_id == node_id or link.target_node_id == node_id
        ]
        for lid in links_to_remove:
            del self._links[lid]
        del self._nodes[node_id]
        self.node_count = len(self._nodes)
        self.link_count = len(self._links)
        self.updated_at = datetime.now(timezone.utc)

    def update_node(self, node_id: str, **kwargs) -> KnowledgeNode:
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found in graph")
        node = self._nodes[node_id]
        for key, value in kwargs.items():
            if hasattr(node, key) and key not in ("node_id", "graph_id"):
                setattr(node, key, value)
        node.version += 1
        node.updated_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        return node

    def add_link(self, link: KnowledgeLink) -> None:
        if link.link_id in self._links:
            raise ValueError(f"Link {link.link_id} already exists in graph")
        if link.source_node_id not in self._nodes:
            raise ValueError(f"Source node {link.source_node_id} not found")
        if link.target_node_id not in self._nodes:
            raise ValueError(f"Target node {link.target_node_id} not found")
        self._links[link.link_id] = link
        self.link_count = len(self._links)
        self.updated_at = datetime.now(timezone.utc)

    def remove_link(self, link_id: str) -> None:
        if link_id not in self._links:
            raise ValueError(f"Link {link_id} not found in graph")
        del self._links[link_id]
        self.link_count = len(self._links)
        self.updated_at = datetime.now(timezone.utc)

    def update_link(self, link_id: str, **kwargs) -> KnowledgeLink:
        if link_id not in self._links:
            raise ValueError(f"Link {link_id} not found in graph")
        link = self._links[link_id]
        for key, value in kwargs.items():
            if hasattr(link, key) and key not in ("link_id", "graph_id"):
                setattr(link, key, value)
        link.version += 1
        link.updated_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        return link

    def get_neighbors(self, node_id: str, depth: int = 1) -> list[KnowledgeNode]:
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found in graph")
        visited = {node_id}
        current_level = {node_id}
        result = []
        for _ in range(depth):
            next_level = set()
            for nid in current_level:
                for link in self._links.values():
                    neighbor = None
                    if link.source_node_id == nid and link.target_node_id not in visited:
                        neighbor = link.target_node_id
                    elif link.target_node_id == nid and link.source_node_id not in visited:
                        neighbor = link.source_node_id
                    if neighbor and neighbor in self._nodes:
                        next_level.add(neighbor)
                        visited.add(neighbor)
                        result.append(self._nodes[neighbor])
            current_level = next_level
        return result

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(node_id)

    def get_link(self, link_id: str) -> Optional[KnowledgeLink]:
        return self._links.get(link_id)

    def get_all_nodes(self) -> list[KnowledgeNode]:
        return list(self._nodes.values())

    def get_all_links(self) -> list[KnowledgeLink]:
        return list(self._links.values())

    def get_nodes_by_type(self, node_type: str) -> list[KnowledgeNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_links_by_type(self, link_type: str) -> list[KnowledgeLink]:
        return [l for l in self._links.values() if l.link_type == link_type]

    def propagate_impact(self, source_node_id: str, depth: int = 3) -> dict:
        if source_node_id not in self._nodes:
            raise ValueError(f"Node {source_node_id} not found")
        affected = []
        paths = []
        visited = {source_node_id}
        queue = [(source_node_id, [], 0)]
        while queue:
            current_id, path, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            for link in self._links.values():
                neighbor = None
                if link.source_node_id == current_id and link.target_node_id not in visited:
                    neighbor = link.target_node_id
                elif link.target_node_id == current_id and link.source_node_id not in visited:
                    neighbor = link.source_node_id
                if neighbor and neighbor in self._nodes:
                    visited.add(neighbor)
                    new_path = path + [link.link_type]
                    affected.append({
                        "node_id": neighbor,
                        "node_type": self._nodes[neighbor].node_type,
                        "depth": current_depth + 1,
                        "path": new_path,
                        "confidence": float(link.confidence) * (0.8 ** current_depth),
                    })
                    paths.append(new_path)
                    queue.append((neighbor, new_path, current_depth + 1))
        return {
            "source_node_id": source_node_id,
            "affected_nodes": affected,
            "impact_paths": paths,
            "total_affected": len(affected),
            "propagation_depth": depth,
        }

    def create_snapshot(self) -> dict:
        return {
            "graph_id": self.graph_id,
            "graph_version": self.version,
            "node_count": self.node_count,
            "link_count": self.link_count,
            "nodes": [
                {"node_id": n.node_id, "node_type": n.node_type, "name": n.name, "version": n.version}
                for n in self._nodes.values()
            ],
            "links": [
                {"link_id": l.link_id, "source": l.source_node_id, "target": l.target_node_id, "type": l.link_type}
                for l in self._links.values()
            ],
        }