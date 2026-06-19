from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import ConnectionType, DefinitionStatus, NodeType
from src.domain.value_objects.parameter_mapping import ParameterMapping


class WorkflowNode(BaseModel):
    node_id: str
    type: NodeType
    name: str
    handler: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 3600
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_retries": 3, "delay_seconds": 60})
    failure_strategy: str = "Retry"


class WorkflowEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    connection_type: ConnectionType = ConnectionType.Sequence
    condition: str = ""





class WorkflowDefinition(BaseModel):
    definition_id: str = ""
    name: str
    version: int = 1
    status: DefinitionStatus = DefinitionStatus.Draft
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    parameter_mappings: list[ParameterMapping] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def validate_dag(self) -> dict[str, Any]:
        if not self.nodes:
            return {"valid": False, "errors": ["Workflow must have at least one node"]}

        node_ids = {n.node_id for n in self.nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}

        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                return {"valid": False, "errors": [f"Edge references non-existent node: {edge.source_id}->{edge.target_id}"]}
            adjacency[edge.source_id].append(edge.target_id)

        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycle_path: list[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    cycle_path.append(neighbor)
                    return True
            rec_stack.remove(node)
            return False

        for nid in node_ids:
            if nid not in visited:
                if dfs(nid):
                    return {"valid": False, "errors": [f"Circular dependency detected involving: {cycle_path}"]}

        for node in self.nodes:
            if node.type == NodeType.SubWorkflow:
                if not node.config.get("sub_workflow_definition_id"):
                    return {"valid": False, "errors": [f"SubWorkflow node {node.node_id} missing sub_workflow_definition_id"]}

        return {"valid": True, "errors": []}

    def publish(self) -> None:
        validation = self.validate_dag()
        if not validation["valid"]:
            raise ValueError(f"Cannot publish: {validation['errors']}")
        self.status = DefinitionStatus.Published
        self.updated_at = datetime.utcnow()

    def deprecate(self) -> None:
        self.status = DefinitionStatus.Deprecated
        self.updated_at = datetime.utcnow()