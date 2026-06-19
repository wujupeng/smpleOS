from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class Entity:
    def __init__(self, entity_id: str | None = None) -> None:
        self.id: str = entity_id or str(uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class ValueObject:
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


class AggregateRoot(Entity):
    def __init__(self, entity_id: str | None = None) -> None:
        super().__init__(entity_id)
        self._domain_events: list[DomainEvent] = []

    @property
    def domain_events(self) -> list[DomainEvent]:
        return list(self._domain_events)

    def add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def clear_domain_events(self) -> list[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events


class DomainEvent:
    def __init__(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        self.event_id: str = event_id or str(uuid.uuid4())
        self.event_type: str = event_type
        self.aggregate_id: str = aggregate_id
        self.payload: dict[str, Any] = payload or {}
        self.occurred_at: datetime = occurred_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
        }