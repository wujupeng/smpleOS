from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aeroforge_common.domain.base import DomainEvent


class EventBus(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        ...

    @abstractmethod
    async def publish_batch(self, events: list[DomainEvent]) -> None:
        ...

    @abstractmethod
    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        ...


class EventHandler(ABC):
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        ...