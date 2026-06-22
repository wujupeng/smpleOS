import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def handle_configuration_updated_event(msg):
    try:
        data = json.loads(msg.data.decode())
        event_id = data.get("event_id", "unknown")
        configuration_id = data.get("configuration_id", "unknown")
        change_type = data.get("change_type", "UNKNOWN")
        received_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"ConfigurationUpdatedEvent received: event_id={event_id}, "
            f"configuration_id={configuration_id}, change_type={change_type}, received_at={received_at}"
        )
        await msg.ack()
    except Exception as e:
        logger.error(f"Error handling ConfigurationUpdatedEvent: {e}")
        await msg.nak()


async def register_config_consumer(bus):
    await bus.subscribe_jetstream(
        subject="aeroforge.config.configuration.updated",
        durable_name="physics-twin-config-consumer",
        callback=handle_configuration_updated_event,
        stream="AEROFORGE_CONFIG",
    )