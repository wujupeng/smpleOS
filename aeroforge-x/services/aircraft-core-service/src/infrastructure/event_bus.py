import json
import os
from typing import Any

import nats


class EventBus:
    def __init__(self):
        self._nc = None
        self._servers = os.getenv("NATS_SERVERS", "nats://localhost:4222")

    async def connect(self):
        self._nc = await nats.connect(self._servers)

    async def close(self):
        if self._nc:
            await self._nc.close()
            self._nc = None

    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        if self._nc is None:
            await self.connect()
        payload = json.dumps(data, default=str).encode()
        await self._nc.publish(subject, payload)

    async def subscribe(self, subject: str, callback):
        if self._nc is None:
            await self.connect()
        await self._nc.subscribe(subject, cb=callback)


event_bus = EventBus()