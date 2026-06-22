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
        self._js = None
        self._servers = os.getenv('NATS_SERVERS', 'nats://localhost:4222')

    async def connect(self):
        if not _HAS_NATS:
            logger.warning('NATS library not available, event_bus disabled')
            return
        try:
            self._nc = await nats_lib.connect(self._servers)
            self._js = self._nc.jetstream()
            logger.info(f'NATS connected to {self._servers}, JetStream enabled')
        except Exception as e:
            logger.warning(f'NATS connection failed: {e}, event_bus disabled')
            self._nc = None
            self._js = None

    async def close(self):
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        if not _HAS_NATS or self._nc is None:
            return
        payload = json.dumps(data, default=str).encode()
        await self._nc.publish(subject, payload)

    async def subscribe(self, subject: str, callback):
        if not _HAS_NATS or self._nc is None:
            return
        await self._nc.subscribe(subject, cb=callback)

    async def publish_jetstream(self, subject: str, data: dict[str, Any]) -> None:
        if self._js is None:
            logger.debug(f'JetStream not available, skipping publish to {subject}')
            return
        try:
            payload = json.dumps(data, default=str).encode()
            ack = await self._js.publish(subject, payload)
            logger.info(f'JetStream publish to {subject}, seq={ack.seq}')
        except Exception as e:
            logger.warning(f'JetStream publish failed for {subject}: {e}')

    async def subscribe_jetstream(self, subject: str, durable_name: str, callback, stream: str = "AEROFORGE_CONFIG") -> None:
        if self._js is None:
            logger.warning(f'JetStream not available, skipping subscribe to {subject}')
            return
        try:
            sub = await self._js.pull_subscribe(
                subject=subject,
                durable=durable_name,
                stream=stream,
            )
            logger.info(f'JetStream pull-subscribed to {subject} (durable={durable_name})')
            import asyncio
            async def _consume():
                try:
                    while True:
                        msgs = await sub.fetch(1, timeout=30)
                        for msg in msgs:
                            try:
                                await callback(msg)
                            except Exception as e:
                                logger.error(f'Callback error: {e}')
                                await msg.nak()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.warning(f'Consumer loop error: {e}')
            asyncio.create_task(_consume())
        except Exception as e:
            logger.warning(f'JetStream subscribe failed for {subject}: {e}')


event_bus = EventBus()
