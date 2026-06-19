from __future__ import annotations

import uuid
from collections import deque
from typing import Any

from src.domain.entities.workflow_definition import WorkflowNode, WorkflowEdge
from src.domain.enums import NodeStatus


class PipelineScheduler:

    @staticmethod
    def topological_sort(nodes: list[WorkflowNode], edges: list[WorkflowEdge]) -> list[list[str]]:
        node_ids = {n.node_id for n in nodes}
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}

        for edge in edges:
            if edge.source_id in node_ids and edge.target_id in node_ids:
                adjacency[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1

        levels: list[list[str]] = []
        current_level = [nid for nid, deg in in_degree.items() if deg == 0]
        processed: set[str] = set()

        while current_level:
            levels.append(sorted(current_level))
            next_level = []
            for nid in current_level:
                processed.add(nid)
                for neighbor in adjacency[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0 and neighbor not in processed:
                        next_level.append(neighbor)
            current_level = next_level

        return levels

    @staticmethod
    def pass_data_pipeline(source_output: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
        result = {}
        transform = mapping.get("transform_expression", "")
        for target_param, source_param in mapping.get("mappings", {}).items():
            if source_param in source_output:
                value = source_output[source_param]
                if transform:
                    try:
                        value = eval(transform, {"__builtins__": {}}, {"value": value})
                    except Exception:
                        pass
                result[target_param] = value
        return result

    @staticmethod
    async def execute_pipeline(instance_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            instance_row = await conn.fetchrow(
                "SELECT wi.*, wd.nodes, wd.edges FROM workflow_engine.workflow_instances wi "
                "JOIN workflow_engine.workflow_definitions wd ON wi.definition_id = wd.definition_id "
                "WHERE wi.instance_id = $1",
                instance_id,
            )
            if instance_row is None:
                return {"error": "Instance not found"}

            nodes = [WorkflowNode(**n) for n in instance_row["nodes"]]
            edges = [WorkflowEdge(**e) for e in instance_row["edges"]]

        levels = PipelineScheduler.topological_sort(nodes, edges)
        executed_nodes: list[str] = []

        for level in levels:
            for node_id in level:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE workflow_engine.node_execution_states SET status = 'Running', started_at = NOW() WHERE instance_id = $1 AND node_id = $2",
                        instance_id, node_id,
                    )

                    await conn.execute(
                        "UPDATE workflow_engine.node_execution_states SET status = 'Completed', completed_at = NOW() WHERE instance_id = $1 AND node_id = $2",
                        instance_id, node_id,
                    )
                executed_nodes.append(node_id)

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.workflow_instances SET status = 'Completed', completed_at = NOW() WHERE instance_id = $1",
                instance_id,
            )

        return {"instance_id": instance_id, "executed_nodes": executed_nodes, "status": "Completed"}