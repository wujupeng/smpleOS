from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.entities.workflow_instance import HumanTask


class HumanTaskService:

    @staticmethod
    async def create_task(instance_id: str, node_id: str, task_type: str, assignee: str, deadline: datetime | None = None, pool=None) -> HumanTask:
        task = HumanTask(
            task_id=str(uuid.uuid4()),
            instance_id=instance_id,
            node_id=node_id,
            type=task_type,
            assignee=assignee,
            deadline=deadline,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO workflow_engine.human_tasks (task_id, instance_id, node_id, task_type, assignee, status, deadline) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    task.task_id, instance_id, node_id, task_type, assignee, "Pending", deadline,
                )

        return task

    @staticmethod
    async def approve_task(task_id: str, comments: str = "", pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.human_tasks SET status = 'Approved', decision = 'Approved', comments = $1, completed_at = NOW() WHERE task_id = $2",
                comments, task_id,
            )
        return {"task_id": task_id, "status": "Approved"}

    @staticmethod
    async def reject_task(task_id: str, comments: str = "", pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.human_tasks SET status = 'Rejected', decision = 'Rejected', comments = $1, completed_at = NOW() WHERE task_id = $2",
                comments, task_id,
            )
        return {"task_id": task_id, "status": "Rejected"}

    @staticmethod
    async def decide_task(task_id: str, decision: str, comments: str = "", pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.human_tasks SET status = 'Completed', decision = $1, comments = $2, completed_at = NOW() WHERE task_id = $3",
                decision, comments, task_id,
            )
        return {"task_id": task_id, "decision": decision}

    @staticmethod
    async def escalate_task(task_id: str, escalated_to: str, pool=None) -> dict[str, Any]:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_engine.human_tasks SET status = 'Escalated', escalated_to = $1 WHERE task_id = $2",
                escalated_to, task_id,
            )
        return {"task_id": task_id, "escalated_to": escalated_to}

    @staticmethod
    async def list_pending_tasks(assignee: str | None = None, pool=None) -> list[dict[str, Any]]:
        async with pool.acquire() as conn:
            if assignee:
                rows = await conn.fetch(
                    "SELECT * FROM workflow_engine.human_tasks WHERE assignee = $1 AND status = 'Pending' ORDER BY deadline",
                    assignee,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM workflow_engine.human_tasks WHERE status = 'Pending' ORDER BY deadline"
                )
        return [dict(r) for r in rows]