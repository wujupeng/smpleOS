import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    try:
        import nats
    except ImportError:
        logger.error("nats-py not installed, installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nats-py>=2.7.0"])
        import nats

    servers = os.getenv("NATS_SERVERS", "nats://localhost:4222")
    logger.info(f"Connecting to NATS at {servers}")

    try:
        nc = await nats.connect(servers)
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")
        sys.exit(1)

    js = nc.jetstream()

    try:
        await js.add_stream(
            name="AEROFORGE_CONFIG",
            subjects=["aeroforge.config.>"],
            retention="limits",
            max_msgs=100000,
            max_age=604800,
        )
        logger.info("Stream AEROFORGE_CONFIG created")
    except Exception as e:
        if "already exists" in str(e).lower() or "stream name already in use" in str(e).lower():
            logger.info("Stream AEROFORGE_CONFIG already exists (idempotent)")
        else:
            logger.warning(f"Stream creation issue: {e}")


    await nc.close()
    logger.info("NATS JetStream initialization complete")


if __name__ == "__main__":
    asyncio.run(main())