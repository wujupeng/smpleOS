"""AeroForge-X v6.0 NATS JetStream Stream Extension

Extends AEROFORGE stream with v6.0 event subjects for:
- Program-H: Configuration Management events
- Program-I: Certification Digital Thread events
- Program-J: Supplier Digital Thread events
- Program-K: Real-time Digital Factory events
- Program-E+: UQ/7-Discipline MDO/GD&T events
"""

import asyncio
import json

import nats


async def init_v6_streams():
    nc = await nats.connect("nats://localhost:4222")
    js = nc.jetstream()

    try:
        await js.update_stream(
            name="AEROFORGE",
            subjects=[
                "aeroforge.>",
            ],
            config={
                "max_msgs": 5_000_000,
                "max_age": 30 * 24 * 3600 * 1e9,
            },
        )
    except Exception:
        await js.add_stream(
            name="AEROFORGE",
            subjects=["aeroforge.>"],
            config={
                "max_msgs": 5_000_000,
                "max_age": 30 * 24 * 3600 * 1e9,
            },
        )

    # V605.1: Program-H Configuration Management events
    program_h_subjects = [
        "aeroforge.v6.config.change.submitted",
        "aeroforge.v6.config.change.approved",
        "aeroforge.v6.config.change.propagated",
        "aeroforge.v6.config.baseline.established",
        "aeroforge.v6.config.baseline.compared",
        "aeroforge.v6.config.conflict.detected",
    ]

    # V605.2: Program-I Certification Digital Thread events
    program_i_subjects = [
        "aeroforge.v6.cert.trace.link.created",
        "aeroforge.v6.cert.trace.broken.detected",
        "aeroforge.v6.cert.trace.gap.alert",
        "aeroforge.v6.cert.checklist.generated",
        "aeroforge.v6.cert.evidence.linked",
        "aeroforge.v6.cert.evidence.package.assembled",
        "aeroforge.v6.cert.evidence.package.locked",
        "aeroforge.v6.cert.evidence.package.exported",
        "aeroforge.v6.cert.regulation.updated",
    ]

    # V605.3: Program-J Supplier Digital Thread events
    program_j_subjects = [
        "aeroforge.v6.supplier.registered",
        "aeroforge.v6.supplier.approved",
        "aeroforge.v6.supplier.quality.issue.created",
        "aeroforge.v6.supplier.car.created",
        "aeroforge.v6.supplier.car.overdue",
        "aeroforge.v6.supplier.car.verified",
        "aeroforge.v6.supplier.rating.downgrade",
        "aeroforge.v6.supplier.lot.non_conforming",
        "aeroforge.v6.supplier.ndt.reject",
    ]

    # V605.4: Program-K Real-time Digital Factory events
    program_k_subjects = [
        "aeroforge.v6.factory.equipment.status",
        "aeroforge.v6.factory.operation.complete",
        "aeroforge.v6.factory.quality.alert",
        "aeroforge.v6.factory.deviation.alert",
        "aeroforge.v6.factory.agv.task.update",
        "aeroforge.v6.factory.bottleneck.detected",
    ]

    # V605.5: Program-E+ UQ/7-Discipline MDO/GD&T events
    program_e_plus_subjects = [
        "aeroforge.v6.uq.high_uncertainty",
        "aeroforge.v6.uq.method.swapped",
        "aeroforge.v6.mdo.7d.started",
        "aeroforge.v6.mdo.7d.generation_completed",
        "aeroforge.v6.mdo.7d.converged",
        "aeroforge.v6.mdo.7d.failed",
        "aeroforge.v6.gdt.annotation.created",
        "aeroforge.v6.gdt.tolerance_chain.analyzed",
        "aeroforge.v6.gdt.deviation.assessed",
    ]

    v6_subjects = (
        program_h_subjects
        + program_i_subjects
        + program_j_subjects
        + program_k_subjects
        + program_e_plus_subjects
    )

    for subject in v6_subjects:
        try:
            await js.publish(subject, json.dumps({"init": True, "version": "6.0"}).encode())
        except Exception:
            pass

    # V605.6: v6.0 Consumers
    consumers = [
        {"name": "v6-config-consumer", "filter": "aeroforge.v6.config.>"},
        {"name": "v6-cert-consumer", "filter": "aeroforge.v6.cert.>"},
        {"name": "v6-supplier-consumer", "filter": "aeroforge.v6.supplier.>"},
        {"name": "v6-factory-consumer", "filter": "aeroforge.v6.factory.>"},
        {"name": "v6-uq-consumer", "filter": "aeroforge.v6.uq.>"},
        {"name": "v6-mdo7d-consumer", "filter": "aeroforge.v6.mdo.7d.>"},
        {"name": "v6-gdt-consumer", "filter": "aeroforge.v6.gdt.>"},
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
    print("v6.0 NATS streams initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_v6_streams())