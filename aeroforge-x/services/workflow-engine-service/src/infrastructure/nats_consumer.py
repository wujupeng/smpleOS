import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def handle_block_updated_event(msg):
    try:
        data = json.loads(msg.data.decode())
        event_id = data.get("event_id", "unknown")
        block_id = data.get("block_id", "unknown")
        received_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"BlockUpdatedEvent received: event_id={event_id}, block_id={block_id}, received_at={received_at}"
        )
        await msg.ack()
    except Exception as e:
        logger.error(f"Error handling BlockUpdatedEvent: {e}")
        await msg.nak()


async def register_config_consumer(bus):
    await bus.subscribe_jetstream(
        subject="aeroforge.config.>",
        durable_name="workflow-engine-config-consumer",
        callback=handle_block_updated_event,
        stream="AEROFORGE_CONFIG",
    )