import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

AEROFORGE_EVENTS_SUBJECTS = [
    "aeroforge.material.lot.created",
    "aeroforge.quality.ndt.completed",
    "aeroforge.quality.car.created",
    "aeroforge.quality.car.closed",
    "aeroforge.cert.evidence.uploaded",
    "aeroforge.config.changed",
]


async def main():
    try:
        import nats
    except ImportError:
        logger.error("nats-py not installed, installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nats-py>=2.7.0"])
        import nats

    servers = os.getenv("NATS_SERVERS", "nats://localhost:4222")
    max_retries = 12
    retry_interval = 5

    nc = None
    for attempt in range(1, max_retries + 1):
        try:
            nc = await nats.connect(servers)
            logger.info(f"Connected to NATS at {servers} (attempt {attempt}/{max_retries})")
            break
        except Exception as e:
            logger.warning(f"NATS connection attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                logger.error(f"Failed to connect to NATS after {max_retries} attempts")
                sys.exit(1)
            await asyncio.sleep(retry_interval)

    js = nc.jetstream()

    try:
        await js.add_stream(
            name="aeroforge-events",
            subjects=AEROFORGE_EVENTS_SUBJECTS,
            retention="limits",
            max_msgs=1000000,
            max_bytes=1073741824,
            max_age=2592000000000000,
            replicas=1,
        )
        logger.info("Created JetStream stream: aeroforge-events")
    except Exception as e:
        if "already exists" in str(e).lower() or "stream name already in use" in str(e).lower():
            logger.info("Stream already exists: aeroforge-events, skipping")
        else:
            logger.warning(f"Stream creation issue: {e}")

    try:
        await js.add_consumer(
            stream="aeroforge-events",
            durable_name="workflow-engine-consumer",
            ack_policy="explicit",
            max_deliver=3,
            filter_subject="aeroforge.>",
        )
        logger.info("Created durable consumer: workflow-engine-consumer")
    except Exception as e:
        if "consumer already exists" in str(e).lower():
            logger.info("Consumer already exists: workflow-engine-consumer, skipping")
        else:
            logger.warning(f"Consumer creation issue: {e}")

    try:
        await js.add_stream(
            name="AEROFORGE_CONFIG",
            subjects=["aeroforge.config.>"],
            retention="limits",
            max_msgs=100000,
            max_age=604800000000000,
        )
        logger.info("Created JetStream stream: AEROFORGE_CONFIG")
    except Exception as e:
        if "already exists" in str(e).lower() or "stream name already in use" in str(e).lower():
            logger.info("Stream already exists: AEROFORGE_CONFIG, skipping")
        else:
            logger.warning(f"Stream creation issue: {e}")

    await nc.close()
    logger.info("NATS JetStream initialization complete")


if __name__ == "__main__":
    asyncio.run(main())
