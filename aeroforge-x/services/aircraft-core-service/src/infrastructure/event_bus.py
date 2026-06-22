import json
import os
import logging
from typing import Any

try:
    import nats as nats_lib
    _HAS_NATS = True
except ImportError:
    _HAS_NATS = False

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._nc = None
        self._servers = os.getenv('NATS_SERVERS', 'nats://localhost:4222')

    async def connect(self):
        if not _HAS_NATS:
            logger.warning('NATS library not available, event_bus disabled')
            return
        self._nc = await nats_lib.connect(self._servers)

    async def close(self):
        if self._nc:
            await self._nc.close()
            self._nc = None

    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        if not _HAS_NATS or self._nc is None:
            return
        payload = json.dumps(data, default=str).encode()
        await self._nc.publish(subject, payload)

    async def subscribe(self, subject: str, callback):
        if not _HAS_NATS or self._nc is None:
            return
        await self._nc.subscribe(subject, cb=callback)


event_bus = EventBus()
