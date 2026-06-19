from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.entities.workflow_instance import WorkflowInstance, NodeExecutionState
from src.domain.enums import InstanceStatus, NodeStatus


class WorkflowExecutionService:

    @staticmethod
    async def start_instance(definition_id: str, definition_version: int, input_parameters: dict[str, Any] | None = None, pool=None) -> WorkflowInstance:
        instance = WorkflowInstance(
            instance_id=str(uuid.uuid4()),
            definition_id=definition_id,
            definition_version=definition_version,
            input_parameters=input_parameters or {},
        )

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT nodes FROM workflow_engine.workflow_definitions WHERE definition_id = $1",
                definition_id,
            )
            if row:
                for node_data in row["nodes"]:
                    instance.node_states.append(NodeExecutionState(node_id=node_data.get("node_id", "")))

        instance.start()

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO workflow_engine.workflow_instances (instance_id, definition_id, definition_version, status, input_parameters, context, started_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    instance.instance_id, definition_id, definition_version,
                    instance.status.value, instance.input_parameters, instance.context,
                    instance.started_at,
                )
                for ns in instance.node_states:
                    await conn.execute(
                        "INSERT INTO workflow_engine.node_execution_states (id, instance_id, node_id, status) VALUES ($1, $2, $3, $4)",
                        str(uuid.uuid4()), instance.instance_id, ns.node_id, ns.status.value,
                    )

        return instance

    @staticmethod
    async def get_instance_status(instance_id: str, pool) -> dict[str, Any] | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_engine.workflow_instances WHERE instance_id = $1", instance_id
            )
            if row is None:
                return None

            node_states = await conn.fetch(
                "SELECT * FROM workflow_engine.node_execution_states WHERE instance_id = $1", instance_id
            )

        result = dict(row)
        result["node_states"] = [dict(ns) for ns in node_states]
        return result

    @staticmethod
    async def suspend_instance(instance_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.workflow_instances SET status = 'Suspended' WHERE instance_id = $1",
                instance_id,
            )
        return {"instance_id": instance_id, "status": "Suspended"}

    @staticmethod
    async def resume_instance(instance_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.workflow_instances SET status = 'Running' WHERE instance_id = $1",
                instance_id,
            )
        return {"instance_id": instance_id, "status": "Running"}

    @staticmethod
    async def cancel_instance(instance_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.workflow_instances SET status = 'Failed', completed_at = NOW() WHERE instance_id = $1",
                instance_id,
            )
        return {"instance_id": instance_id, "status": "Failed"}

    @staticmethod
    async def retry_node(instance_id: str, node_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_engine.node_execution_states WHERE instance_id = $1 AND node_id = $2",
                instance_id, node_id,
            )
            if row is None:
                return {"error": "Node state not found"}

            new_retry = row["retry_count"] + 1
            await conn.execute(
                "UPDATE workflow_engine.node_execution_states SET status = 'Pending', retry_count = $1, error_message = '' WHERE instance_id = $2 AND node_id = $3",
                new_retry, instance_id, node_id,
            )
            await conn.execute(
                "UPDATE workflow_engine.workflow_instances SET status = 'Running' WHERE instance_id = $1 AND status = 'Failed'",
                instance_id,
            )

        return {"instance_id": instance_id, "node_id": node_id, "retry_count": new_retry, "status": "Pending"}