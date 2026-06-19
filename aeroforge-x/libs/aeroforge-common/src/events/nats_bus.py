from __future__ import annotations

import json
import logging
from typing import Any

import nats
from nats.js import JetStreamContext

from aeroforge_common.domain.base import DomainEvent
from aeroforge_common.events.event_bus import EventBus, EventHandler

logger = logging.getLogger(__name__)


class NATSEventBus(EventBus):
    def __init__(self, nats_url: str = "nats://localhost:4222") -> None:
        self._nats_url = nats_url
        self._nc: nats.NATS | None = None
        self._js: JetStreamContext | None = None
        self._handlers: dict[str, list[EventHandler]] = {}

    async def connect(self) -> None:
        self._nc = await nats.connect(self._nats_url)
        self._js = self._nc.jetstream()
        try:
            await self._js.add_stream(name="AEROFORGE", subjects=["aircraft.>", "ebom.>", "workorder.>", "inspection.>", "ecr.>", "twin.>"])
        except Exception:
            logger.info("Stream AEROFORGE already exists or creation skipped")
        logger.info("Connected to NATS JetStream at %s", self._nats_url)

    async def close(self) -> None:
        if self._nc is not None:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish(self, event: DomainEvent) -> None:
        if self._js is None:
            raise RuntimeError("NATS not connected. Call connect() first.")
        payload = json.dumps(event.to_dict()).encode("utf-8")
        await self._js.publish(subject=event.event_type, payload=payload)
        logger.info("Published event: %s (id=%s)", event.event_type, event.event_id)

    async def publish_batch(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if self._js is None:
            raise RuntimeError("NATS not connected. Call connect() first.")

        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

        async def _callback(msg: nats.aio.msg.Msg) -> None:
            data = json.loads(msg.data.decode("utf-8"))
            event = DomainEvent(
                event_id=data["event_id"],
                event_type=data["event_type"],
                aggregate_id=data["aggregate_id"],
                payload=data.get("payload", {}),
                occurred_at=__import__("datetime").datetime.fromisoformat(data["occurred_at"]),
            )
            for h in self._handlers.get(event_type, []):
                try:
                    await h.handle(event)
                except Exception:
                    logger.exception("Error handling event %s", event.event_type)
            await msg.ack()

        subject = event_type
        durable = f"durable-{event_type.replace('.', '-')}"
        await self._js.subscribe(subject=subject, queue=durable, cb=_callback, durable=durable, stream="AEROFORGE")
        logger.info("Subscribed to event type: %s", event_type)