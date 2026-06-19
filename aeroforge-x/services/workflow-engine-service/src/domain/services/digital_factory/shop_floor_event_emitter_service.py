"""AeroForge-X v6.0 ShopFloorEventEmitterService

Manages shop floor event-driven integration: equipment status changes,
operation events, quality alerts, deviation alerts, and historical playback.
REQ-FACTORY-019~022
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ShopFloorEventType(str, Enum):
    EQUIPMENT_STATUS_CHANGE = "EquipmentStatusChange"
    OPERATION_START = "OperationStart"
    OPERATION_COMPLETE = "OperationComplete"
    QUALITY_ALERT = "QualityAlert"
    AGV_TASK_UPDATE = "AGVTaskUpdate"
    DEVIATION_ALERT = "DeviationAlert"


@dataclass
class ShopFloorEvent:
    event_id: str
    event_type: ShopFloorEventType
    source_equipment_id: str
    payload: dict = field(default_factory=dict)
    emitted_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_equipment_id": self.source_equipment_id,
            "payload": self.payload,
            "emitted_at": self.emitted_at,
        }


@dataclass
class EventReceipt:
    event_id: str
    published: bool
    subject: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "published": self.published,
            "subject": self.subject,
        }


@dataclass
class EventFilter:
    event_type: ShopFloorEventType | None = None
    source_equipment_id: str = ""
    time_from: float = 0
    time_to: float = 0


class ShopFloorEventEmitterService:

    EVENT_SUBJECT_MAP = {
        ShopFloorEventType.EQUIPMENT_STATUS_CHANGE: "aeroforge.v6.factory.equipment.status",
        ShopFloorEventType.OPERATION_START: "aeroforge.v6.factory.operation.complete",
        ShopFloorEventType.OPERATION_COMPLETE: "aeroforge.v6.factory.operation.complete",
        ShopFloorEventType.QUALITY_ALERT: "aeroforge.v6.factory.quality.alert",
        ShopFloorEventType.AGV_TASK_UPDATE: "aeroforge.v6.factory.agv.task.update",
        ShopFloorEventType.DEVIATION_ALERT: "aeroforge.v6.factory.deviation.alert",
    }

    DEFAULT_PLAYBACK_WINDOW_S = 30 * 24 * 3600

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._events: list[ShopFloorEvent] = []

    def _emit_event(
        self, event_type: ShopFloorEventType, equipment_id: str, payload: dict
    ) -> EventReceipt:
        event = ShopFloorEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            source_equipment_id=equipment_id,
            payload=payload,
        )
        self._events.append(event)

        subject = self.EVENT_SUBJECT_MAP.get(event_type, "aeroforge.v6.factory.>")
        return EventReceipt(
            event_id=event.event_id,
            published=True,
            subject=subject,
        )

    def emitEquipmentStatusChange(
        self, equipment_id: str, new_status: str
    ) -> EventReceipt:
        return self._emit_event(
            ShopFloorEventType.EQUIPMENT_STATUS_CHANGE,
            equipment_id,
            {"new_status": new_status},
        )

    def emitOperationEvent(
        self, operation_id: str, event_type: str
    ) -> EventReceipt:
        sf_type = (
            ShopFloorEventType.OPERATION_START
            if event_type == "start"
            else ShopFloorEventType.OPERATION_COMPLETE
        )
        return self._emit_event(
            sf_type,
            operation_id,
            {"operation_id": operation_id, "event": event_type},
        )

    def emitQualityAlert(
        self, equipment_id: str, alert_data: dict
    ) -> EventReceipt:
        return self._emit_event(
            ShopFloorEventType.QUALITY_ALERT,
            equipment_id,
            alert_data,
        )

    def emitDeviationAlert(
        self, equipment_id: str, deviation_data: dict
    ) -> EventReceipt:
        return self._emit_event(
            ShopFloorEventType.DEVIATION_ALERT,
            equipment_id,
            deviation_data,
        )

    def playbackEvents(
        self, event_filter: EventFilter, time_window_s: float | None = None
    ) -> list[ShopFloorEvent]:
        window = time_window_s or self.DEFAULT_PLAYBACK_WINDOW_S
        cutoff = time.time() - window

        results = []
        for event in self._events:
            if event.emitted_at < cutoff:
                continue
            if event_filter.event_type and event.event_type != event_filter.event_type:
                continue
            if event_filter.source_equipment_id and event.source_equipment_id != event_filter.source_equipment_id:
                continue
            if event_filter.time_from and event.emitted_at < event_filter.time_from:
                continue
            if event_filter.time_to and event.emitted_at > event_filter.time_to:
                continue
            results.append(event)

        return results