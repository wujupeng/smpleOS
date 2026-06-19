from __future__ import annotations

import uuid
from typing import Any

from src.domain.entities.workflow_instance import EventTrigger
from src.domain.enums import TriggerType


class EventTriggerService:

    @staticmethod
    async def create_trigger(
        definition_id: str,
        trigger_type: TriggerType,
        event_pattern: str = "",
        cron_expression: str = "",
        condition: str = "",
        pool=None,
    ) -> EventTrigger:
        trigger = EventTrigger(
            trigger_id=str(uuid.uuid4()),
            definition_id=definition_id,
            trigger_type=trigger_type.value,
            event_pattern=event_pattern,
            cron_expression=cron_expression,
            condition=condition,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO workflow_engine.event_triggers (trigger_id, definition_id, trigger_type, event_pattern, cron_expression, condition, enabled) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    trigger.trigger_id, definition_id, trigger_type.value,
                    event_pattern, cron_expression, condition, True,
                )

        return trigger

    @staticmethod
    async def handle_event(event_subject: str, event_data: dict[str, Any], pool) -> list[dict[str, Any]]:
        async with pool.acquire() as conn:
            triggers = await conn.fetch(
                "SELECT * FROM workflow_engine.event_triggers WHERE trigger_type = 'EventDriven' AND event_pattern = $1 AND enabled = TRUE",
                event_subject,
            )

            started_instances = []
            for trigger_row in triggers:
                definition_id = trigger_row["definition_id"]
                def_row = await conn.fetchrow(
                    "SELECT status FROM workflow_engine.workflow_definitions WHERE definition_id = $1",
                    definition_id,
                )
                if def_row and def_row["status"] == "Published":
                    from src.domain.services.workflow_execution_service import WorkflowExecutionService
                    instance = await WorkflowExecutionService.start_instance(
                        definition_id=definition_id,
                        definition_version=1,
                        input_parameters=event_data,
                        pool=pool,
                    )
                    started_instances.append({"instance_id": instance.instance_id, "definition_id": definition_id})

        return started_instances

    @staticmethod
    async def test_trigger(trigger_id: str, pool) -> dict[str, Any]:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_engine.event_triggers WHERE trigger_id = $1", trigger_id
            )
            if row is None:
                return {"connected": False, "error": "Trigger not found"}

            return {"connected": True, "trigger_id": trigger_id, "trigger_type": row["trigger_type"]}