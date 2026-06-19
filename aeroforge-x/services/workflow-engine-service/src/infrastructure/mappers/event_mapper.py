from typing import Any

EVENT_MAPPINGS: list[dict[str, str]] = [
    {
        "v1_event": "design.baseline.frozen",
        "trigger_name": "DesignVerificationTrigger",
        "workflow_template": "DesignVerificationWorkflow",
    },
    {
        "v1_event": "ebom.generated",
        "trigger_name": "ManufacturingExecutionTrigger",
        "workflow_template": "ManufacturingExecutionWorkflow",
    },
    {
        "v1_event": "cert.compliance.verified",
        "trigger_name": "CertificationTrigger",
        "workflow_template": "CertificationWorkflow",
    },
    {
        "v1_event": "ecr.approved",
        "trigger_name": "ChangeManagementTrigger",
        "workflow_template": "ChangeManagementWorkflow",
    },
    {
        "v1_event": "fleet.twin.anomaly.detected",
        "trigger_name": "FRACASTrigger",
        "workflow_template": "FRACASWorkflow",
    },
    {
        "v1_event": "fracas.report.created",
        "trigger_name": "AirworthinessReviewTrigger",
        "workflow_template": "AirworthinessReviewWorkflow",
    },
]


def get_event_mapping(v1_event: str) -> dict[str, str] | None:
    for mapping in EVENT_MAPPINGS:
        if mapping["v1_event"] == v1_event:
            return mapping
    return None


def get_all_mappings() -> list[dict[str, str]]:
    return EVENT_MAPPINGS.copy()