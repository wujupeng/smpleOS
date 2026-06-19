"""AeroForge-X V6.1 NATS JetStream Stream Extension

Adds V6.1 event subjects for:
- DG: Dataset Governance events
- MC: PHM Model Confidence events
- IC: BOM Incremental Propagation events
"""

import asyncio

import nats


V61_SUBJECTS = [
    "aeroforge.v6.dataset.drift.detected",
    "aeroforge.v6.dataset.quality.degraded",
    "aeroforge.v6.phm.confidence.updated",
    "aeroforge.v6.bom.propagation.fallback",
]

V61_CONSUMERS = [
    {"name": "v61-dataset-consumer", "filter": "aeroforge.v6.dataset.>"},
    {"name": "v61-phm-consumer", "filter": "aeroforge.v6.phm.>"},
    {"name": "v61-bom-consumer", "filter": "aeroforge.v6.bom.>"},
]


async def init_v61_streams():
    nc = await nats.connect("nats://localhost:4222")
    js = nc.jetstream()

    try:
        stream = await js.stream_info("AEROFORGE")
        existing_subjects = list(stream.config.subjects) if stream.config.subjects else ["aeroforge.>"]

        new_subjects = list(set(existing_subjects) | set(V61_SUBJECTS))
        if "aeroforge.>" not in new_subjects:
            new_subjects.append("aeroforge.>")

        await js.update_stream(
            name="AEROFORGE",
            subjects=new_subjects,
        )
        print(f"Updated AEROFORGE stream with {len(V61_SUBJECTS)} V6.1 subjects")
    except Exception:
        print("AEROFORGE stream not found, creating with V6.1 subjects")
        await js.add_stream(
            name="AEROFORGE",
            subjects=["aeroforge.>"],
            config={"max_msgs": 5_000_000},
        )

    for consumer in V61_CONSUMERS:
        try:
            await js.add_consumer(
                "AEROFORGE",
                durable_name=consumer["name"],
                filter_subject=consumer["filter"],
            )
            print(f"Created V6.1 consumer: {consumer['name']}")
        except Exception:
            print(f"V6.1 consumer already exists: {consumer['name']}")

    await nc.close()
    print("V6.1 NATS JetStream initialization complete")


if __name__ == "__main__":
    asyncio.run(init_v61_streams())