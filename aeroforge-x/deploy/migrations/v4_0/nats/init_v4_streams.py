"""AeroForge-X v4.0 NATS JetStream Stream Extension

Extends AEROFORGE stream with v4.0 event subjects for:
- Aerodynamic Database events
- Pack Battery thermal/safety events
- Flight Mode Manager transition events
- Multi-body dynamics warning events
- Test Evidence Center events
"""

import asyncio
import json

import nats


async def init_v4_streams():
    nc = await nats.connect("nats://localhost:4222")
    js = nc.jetstream()

    try:
        await js.update_stream(
            name="AEROFORGE",
            subjects=[
                "aeroforge.>",
            ],
            config={
                "max_msgs": 2_000_000,
                "max_age": 14 * 24 * 3600 * 1e9,
            },
        )
    except Exception:
        await js.add_stream(
            name="AEROFORGE",
            subjects=["aeroforge.>"],
            config={
                "max_msgs": 2_000_000,
                "max_age": 14 * 24 * 3600 * 1e9,
            },
        )

    v4_subjects = [
        "aeroforge.aero.database.loaded",
        "aeroforge.aero.database.switched",
        "aeroforge.aero.database.hot_reloaded",
        "aeroforge.aero.database.import.completed",
        "aeroforge.aero.database.import.failed",
        "aeroforge.aero.database.validated",
        "aeroforge.battery.thermal_runaway.detected",
        "aeroforge.battery.thermal_runaway.propagated",
        "aeroforge.battery.low_soc_pack",
        "aeroforge.battery.bms.protection_activated",
        "aeroforge.battery.bms.fault_isolated",
        "aeroforge.fmm.mode_transition.requested",
        "aeroforge.fmm.mode_transition.completed",
        "aeroforge.fmm.mode_transition.rejected",
        "aeroforge.fmm.envelope_protection.activated",
        "aeroforge.fmm.emergency_override.activated",
        "aeroforge.mbd.flutter_warning",
        "aeroforge.mbd.divergence_warning",
        "aeroforge.mbd.fatigue_limit_warning",
        "aeroforge.tec.test_result.ingested",
        "aeroforge.tec.coverage_regression",
        "aeroforge.tec.benchmark_regression",
        "aeroforge.tec.evidence_chain.completed",
        "aeroforge.tec.evidence_chain.gap_detected",
    ]

    for subject in v4_subjects:
        try:
            await js.publish(subject, json.dumps({"init": True, "version": "4.0"}).encode())
        except Exception:
            pass

    consumers = [
        {"name": "v4-aero-consumer", "filter": "aeroforge.aero.>"},
        {"name": "v4-battery-consumer", "filter": "aeroforge.battery.>"},
        {"name": "v4-fmm-consumer", "filter": "aeroforge.fmm.>"},
        {"name": "v4-mbd-consumer", "filter": "aeroforge.mbd.>"},
        {"name": "v4-tec-consumer", "filter": "aeroforge.tec.>"},
    ]

    for c in consumers:
        try:
            await js.add_consumer(
                stream="AEROFORGE",
                durable_name=c["name"],
                filter_subject=c["filter"],
                ack_policy="explicit",
            )
        except Exception:
            pass

    await nc.close()
    print("v4.0 NATS streams initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_v4_streams())