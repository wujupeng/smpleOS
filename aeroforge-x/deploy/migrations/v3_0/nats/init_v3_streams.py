"""
AeroForge-X v3.0 NATS JetStream Stream & Consumer Initialization
Program-C: Automatic Propagation - Event Infrastructure
"""

import asyncio
import json
import os

import nats
from nats.js.api import StreamConfig, ConsumerConfig, RetentionPolicy, DiscardPolicy


NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")


async def init_v3_streams():
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    stream_name = "AEROFORGE_V3"
    subjects = [
        "aeroforge.aircraft.object.created",
        "aeroforge.aircraft.object.updated",
        "aeroforge.aircraft.object.deleted",
        "aeroforge.aircraft.object.transitioned",
        "aeroforge.aircraft.schema.registered",
        "aeroforge.aircraft.schema.published",
        "aeroforge.aircraft.schema.migrated",
        "aeroforge.manufacturing.ebom.generated",
        "aeroforge.manufacturing.mbom.transformed",
        "aeroforge.manufacturing.work_order.created",
        "aeroforge.twin.anomaly.detected",
        "aeroforge.twin.health.warning",
        "aeroforge.twin.health.critical",
        "aeroforge.battery.low_soc",
        "aeroforge.cae.cfd.completed",
        "aeroforge.cae.fea.completed",
        "aeroforge.certification.compliance.changed",
        "aeroforge.fracas.report.created",
    ]

    try:
        await js.add_stream(StreamConfig(
            name=stream_name,
            subjects=subjects,
            retention=RetentionPolicy.LIMITS,
            discard=DiscardPolicy.OLD,
            max_msgs=1_000_000,
            max_age=7 * 24 * 3600 * 1_000_000_000,  # 7 days in nanoseconds
            max_msg_size=1024 * 1024,  # 1MB
            storage="file",
        ))
        print(f"Created stream: {stream_name}")
    except Exception as e:
        if "stream already exists" in str(e).lower():
            print(f"Stream already exists: {stream_name}")
        else:
            raise

    try:
        await js.add_consumer(stream_name, ConsumerConfig(
            name="event-trigger-service-v3",
            filter_subject="aeroforge.aircraft.object.>",
            durable_name="event-trigger-service-v3",
            ack_policy="explicit",
            max_deliver=3,
            ack_wait=30_000_000_000,  # 30s
        ))
        print("Created consumer: event-trigger-service-v3")
    except Exception as e:
        if "consumer already exists" in str(e).lower():
            print("Consumer already exists: event-trigger-service-v3")
        else:
            raise

    try:
        await js.add_consumer(stream_name, ConsumerConfig(
            name="propagation-chain-monitor",
            filter_subject="aeroforge.>",
            durable_name="propagation-chain-monitor",
            ack_policy="explicit",
            max_deliver=3,
            ack_wait=30_000_000_000,
        ))
        print("Created consumer: propagation-chain-monitor")
    except Exception as e:
        if "consumer already exists" in str(e).lower():
            print("Consumer already exists: propagation-chain-monitor")
        else:
            raise

    try:
        await js.add_consumer(stream_name, ConsumerConfig(
            name="twin-anomaly-monitor",
            filter_subject="aeroforge.twin.>",
            durable_name="twin-anomaly-monitor",
            ack_policy="explicit",
            max_deliver=5,
            ack_wait=15_000_000_000,
        ))
        print("Created consumer: twin-anomaly-monitor")
    except Exception as e:
        if "consumer already exists" in str(e).lower():
            print("Consumer already exists: twin-anomaly-monitor")
        else:
            raise

    await nc.close()
    print("NATS v3.0 initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_v3_streams())