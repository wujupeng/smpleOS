import json
import os
import logging
from typing import Any

import nats

logger = logging.getLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_STREAM = "AEROFORGE_EVENTS"


class EventBus:
    def __init__(self):
        self._nc = None
        self._js = None

    async def connect(self):
        self._nc = await nats.connect(NATS_URL)
        self._js = self._nc.jetstream()
        try:
            await self._js.add_stream(name=NATS_STREAM, subjects=["operation.>", "fleet.>", "maintenance.>", "analytics.>", "flight.>"])
        except Exception:
            pass

    async def close(self):
        if self._nc:
            await self._nc.close()

    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        if not self._js:
            await self.connect()
        payload = json.dumps(data, default=str).encode()
        await self._js.publish(subject, payload)
        logger.info(f"Published event: {subject}")


event_bus = EventBus()