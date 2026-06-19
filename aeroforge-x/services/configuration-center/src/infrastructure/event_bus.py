import os
import json
import logging
from typing import Optional, Callable, Any

import nats
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._nc: Optional[nats.NATS] = None
        self._js: Optional[JetStreamContext] = None
        self._url = os.getenv("NATS_URL", "nats://nats:4222")

    async def connect(self):
        self._nc = await nats.connect(self._url)
        self._js = self._nc.jetstream()
        await self._ensure_streams()

    async def disconnect(self):
        if self._nc:
            await self._nc.close()

    def is_connected(self) -> bool:
        return self._nc is not None and not self._nc.is_closed

    async def _ensure_streams(self):
        streams = {
            "CONFIG": {
                "subjects": [
                    "config.item.created",
                    "config.item.updated",
                    "config.item.lifecycle_changed",
                    "config.baseline.created",
                    "config.baseline.frozen",
                    "config.baseline.unfrozen",
                    "config.change.created",
                    "config.change.propagated",
                    "config.change.approved",
                    "config.change.implemented",
                    "config.compatibility.violation",
                ],
            },
        }
        for name, config in streams.items():
            try:
                await self._js.add_stream(name=name, subjects=config["subjects"])
            except Exception:
                pass

    async def publish(self, subject: str, data: dict):
        if not self._js:
            raise RuntimeError("JetStream not initialized")
        payload = json.dumps(data, default=str).encode()
        await self._js.publish(subject, payload)
        logger.info(f"Published event: {subject}")

    async def subscribe(self, subject: str, handler: Callable[[dict], Any], durable: str = None):
        if not self._js:
            raise RuntimeError("JetStream not initialized")

        async def _callback(msg):
            data = json.loads(msg.data.decode())
            try:
                await handler(data)
                await msg.ack()
            except Exception as e:
                logger.error(f"Error handling event {subject}: {e}")
                await msg.nak()

        await self._js.subscribe(subject, durable=durable or subject.replace(".", "_"), cb=_callback)