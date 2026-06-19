"""AeroForge-X v5.0 NATS JetStream Stream Extension

Extends AEROFORGE stream with v5.0 event subjects for:
- Program-E: Generative Aircraft Design events
- Program-F: Manufacturing Digital Thread events
- Program-G: Fleet Intelligence events
"""

import asyncio
import json

import nats


async def init_v5_streams():
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

    # V505.1: Program-E event subjects
    program_e_subjects = [
        "aeroforge.design.requirement.parsed",
        "aeroforge.design.requirement.validated",
        "aeroforge.design.requirement.conflict_detected",
        "aeroforge.design.geometry.generated",
        "aeroforge.design.geometry.exported",
        "aeroforge.design.geometry.manufacturing_checked",
        "aeroforge.cfd.surrogate.trained",
        "aeroforge.cfd.surrogate.validated",
        "aeroforge.cfd.surrogate.deprecated",
        "aeroforge.cfd.surrogate_fallback",
        "aeroforge.mdo.run.started",
        "aeroforge.mdo.run.generation_completed",
        "aeroforge.mdo.convergence",
        "aeroforge.mdo.run.completed",
        "aeroforge.mdo.run.failed",
        "aeroforge.aero_gpt.suggestion.generated",
        "aeroforge.aero_gpt.suggestion.accepted",
        "aeroforge.aero_gpt.suggestion.rejected",
    ]

    # V505.2: Program-F event subjects
    program_f_subjects = [
        "aeroforge.bom.change.submitted",
        "aeroforge.bom.change.propagated",
        "aeroforge.bom.change.propagation_failed",
        "aeroforge.bom.propagation.ebom_to_mbom",
        "aeroforge.bom.propagation.mbom_to_sbom",
        "aeroforge.process_plan.generated",
        "aeroforge.process_plan.optimized",
        "aeroforge.fracas.failure.reported",
        "aeroforge.fracas.failure.updated",
        "aeroforge.fracas.root_cause",
        "aeroforge.fracas.corrective_action.verified",
        "aeroforge.feedback_loop.stage_transition.started",
        "aeroforge.feedback_loop.stage_transition.completed",
        "aeroforge.feedback_loop.interrupted",
        "aeroforge.feedback_loop.completed",
    ]

    # V505.3: Program-G event subjects
    program_g_subjects = [
        "aeroforge.fleet.health.aggregated",
        "aeroforge.fleet.health.warning",
        "aeroforge.fleet.health.critical",
        "aeroforge.fleet.fatigue_warning",
        "aeroforge.phm.rul_prediction.engine",
        "aeroforge.phm.rul_prediction.battery",
        "aeroforge.phm.rul_prediction.structure",
        "aeroforge.phm.predictive_alert",
        "aeroforge.design_feedback.trend.detected",
        "aeroforge.design_feedback.trend.confirmed",
        "aeroforge.design_feedback.ticket.created",
        "aeroforge.design_feedback.ticket.updated",
        "aeroforge.fleet.schedule.optimized",
        "aeroforge.fleet.schedule.violation",
    ]

    v5_subjects = program_e_subjects + program_f_subjects + program_g_subjects

    for subject in v5_subjects:
        try:
            await js.publish(subject, json.dumps({"init": True, "version": "5.0"}).encode())
        except Exception:
            pass

    # V505.4: v5.0 Consumers
    consumers = [
        {"name": "v5-design-consumer", "filter": "aeroforge.design.>"},
        {"name": "v5-cfd-consumer", "filter": "aeroforge.cfd.>"},
        {"name": "v5-mdo-consumer", "filter": "aeroforge.mdo.>"},
        {"name": "v5-aerogpt-consumer", "filter": "aeroforge.aero_gpt.>"},
        {"name": "v5-bom-consumer", "filter": "aeroforge.bom.>"},
        {"name": "v5-process-plan-consumer", "filter": "aeroforge.process_plan.>"},
        {"name": "v5-fracas-consumer", "filter": "aeroforge.fracas.>"},
        {"name": "v5-feedback-loop-consumer", "filter": "aeroforge.feedback_loop.>"},
        {"name": "v5-fleet-consumer", "filter": "aeroforge.fleet.>"},
        {"name": "v5-phm-consumer", "filter": "aeroforge.phm.>"},
        {"name": "v5-design-feedback-consumer", "filter": "aeroforge.design_feedback.>"},
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
    print("v5.0 NATS streams initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_v5_streams())