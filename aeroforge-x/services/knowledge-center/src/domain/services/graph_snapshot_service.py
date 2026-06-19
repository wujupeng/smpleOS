from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from ..entities.knowledge_graph import KnowledgeGraph
from ..value_objects.graph_snapshot import GraphSnapshot

logger = logging.getLogger(__name__)


class GraphSnapshotService:
    def create_snapshot(
        self,
        graph: KnowledgeGraph,
        name: str = "",
        description: str = "",
        created_by: str | None = None,
    ) -> GraphSnapshot:
        snapshot_data = graph.create_snapshot()
        checksum = hashlib.sha256(
            json.dumps(snapshot_data, default=str, sort_keys=True).encode()
        ).hexdigest()
        snapshot = GraphSnapshot(
            graph_id=graph.graph_id,
            graph_version=graph.version,
            name=name or f"snapshot-v{graph.version}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            description=description,
            node_count=graph.node_count,
            link_count=graph.link_count,
            checksum=checksum,
            snapshot_data=snapshot_data,
            created_by=created_by,
        )
        logger.info(
            f"Snapshot created: {snapshot.name} "
            f"(nodes={snapshot.node_count}, links={snapshot.link_count}, "
            f"checksum={snapshot.checksum[:12]}...)"
        )
        return snapshot

    def restore_snapshot(self, graph: KnowledgeGraph, snapshot: GraphSnapshot) -> KnowledgeGraph:
        if snapshot.graph_id != graph.graph_id:
            raise ValueError(f"Snapshot graph_id {snapshot.graph_id} does not match graph {graph.graph_id}")
        self._validate_checksum(snapshot)
        data = snapshot.snapshot_data
        for node_data in data.get("nodes", []):
            existing = graph.get_node(node_data["node_id"])
            if not existing:
                from ..entities.knowledge_node import KnowledgeNode
                node = KnowledgeNode(
                    node_id=node_data["node_id"],
                    graph_id=graph.graph_id,
                    node_type=node_data["node_type"],
                    name=node_data["name"],
                    version=node_data.get("version", 1),
                )
                graph.add_node(node)
        for link_data in data.get("links", []):
            existing = graph.get_link(link_data["link_id"])
            if not existing:
                from ..entities.knowledge_link import KnowledgeLink
                link = KnowledgeLink(
                    link_id=link_data["link_id"],
                    graph_id=graph.graph_id,
                    source_node_id=link_data["source"],
                    target_node_id=link_data["target"],
                    link_type=link_data["type"],
                )
                try:
                    graph.add_link(link)
                except ValueError:
                    pass
        logger.info(f"Snapshot restored: {snapshot.name}")
        return graph

    def compare_snapshots(self, snapshot_a: GraphSnapshot, snapshot_b: GraphSnapshot) -> dict:
        if snapshot_a.graph_id != snapshot_b.graph_id:
            raise ValueError("Cannot compare snapshots from different graphs")
        data_a = snapshot_a.snapshot_data
        data_b = snapshot_b.snapshot_data
        nodes_a = {n["node_id"]: n for n in data_a.get("nodes", [])}
        nodes_b = {n["node_id"]: n for n in data_b.get("nodes", [])}
        added_nodes = [n for nid, n in nodes_b.items() if nid not in nodes_a]
        removed_nodes = [n for nid, n in nodes_a.items() if nid not in nodes_b]
        common_nodes = set(nodes_a.keys()) & set(nodes_b.keys())
        modified_nodes = [
            {"node_id": nid, "from": nodes_a[nid], "to": nodes_b[nid]}
            for nid in common_nodes
            if nodes_a[nid].get("version") != nodes_b[nid].get("version")
        ]
        links_a = {l["link_id"]: l for l in data_a.get("links", [])}
        links_b = {l["link_id"]: l for l in data_b.get("links", [])}
        added_links = [l for lid, l in links_b.items() if lid not in links_a]
        removed_links = [l for lid, l in links_a.items() if lid not in links_b]
        return {
            "snapshot_a": snapshot_a.name,
            "snapshot_b": snapshot_b.name,
            "nodes_added": len(added_nodes),
            "nodes_removed": len(removed_nodes),
            "nodes_modified": len(modified_nodes),
            "links_added": len(added_links),
            "links_removed": len(removed_links),
            "added_nodes_detail": added_nodes,
            "removed_nodes_detail": removed_nodes,
            "modified_nodes_detail": modified_nodes,
            "added_links_detail": added_links,
            "removed_links_detail": removed_links,
        }

    def list_snapshots(self, graph_id: str, snapshots: list[GraphSnapshot]) -> list[GraphSnapshot]:
        return sorted(
            [s for s in snapshots if s.graph_id == graph_id],
            key=lambda s: s.created_at,
            reverse=True,
        )

    def _validate_checksum(self, snapshot: GraphSnapshot) -> None:
        current = hashlib.sha256(
            json.dumps(snapshot.snapshot_data, default=str, sort_keys=True).encode()
        ).hexdigest()
        if current != snapshot.checksum:
            raise ValueError(f"Snapshot checksum mismatch: expected {snapshot.checksum[:12]}, got {current[:12]}")