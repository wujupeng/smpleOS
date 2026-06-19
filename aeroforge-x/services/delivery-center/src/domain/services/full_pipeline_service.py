from __future__ import annotations

import uuid
import random
import time
from datetime import datetime, timezone
from typing import Any

from ..entities.full_pipeline import (
    FullPipelineRun,
    PipelineStage,
    PipelineStatus,
    StageOutput,
    StageStatus,
)


_STAGE_DESCRIPTIONS = {
    PipelineStage.REQUIREMENTS_TO_DESIGN: "需求规格 → 参数化3D模型",
    PipelineStage.DESIGN_TO_ENGINEERING: "3D模型 → 工程模型（机体/结构/动力/线束）",
    PipelineStage.ENGINEERING_TO_CAE: "工程模型 → CAE分析（CFD/FEA/颤振/热/多物理场）",
    PipelineStage.DESIGN_TO_BOM: "设计模型 → eBOM → mBOM → sBOM",
    PipelineStage.BOM_TO_MANUFACTURING: "mBOM → 工艺路线 → 工单 → QC计划",
    PipelineStage.CERTIFICATION: "认证计划 → 符合性验证 → 审定文档",
    PipelineStage.FLIGHT_TEST: "试飞方案生成",
    PipelineStage.DELIVERY_PACKAGE: "完整交付包生成和校验",
}

_STAGE_OUTPUTS = {
    PipelineStage.REQUIREMENTS_TO_DESIGN: {
        "3d_model_id": "model-001",
        "design_parameters": {"wing_span": 15.2, "fuselage_length": 12.8, "mtow": 5700},
        "model_format": "STEP",
    },
    PipelineStage.DESIGN_TO_ENGINEERING: {
        "engineering_models": ["airframe", "structural", "propulsion", "wiring"],
        "parts_count": 1247,
        "interfaces_count": 89,
    },
    PipelineStage.ENGINEERING_TO_CAE: {
        "cae_analyses": ["cfd_lift_drag", "fea_stress", "flutter", "thermal", "multiphysics"],
        "all_passed": True,
        "safety_factors": {"min": 1.52, "max": 3.8},
    },
    PipelineStage.DESIGN_TO_BOM: {
        "ebom_items": 1247,
        "mbom_items": 1583,
        "sbom_items": 2105,
        "make_items": 456,
        "buy_items": 791,
    },
    PipelineStage.BOM_TO_MANUFACTURING: {
        "process_routes": 12,
        "work_orders": 456,
        "qc_plans": 89,
        "estimated_cycle_time_hours": 2400,
    },
    PipelineStage.CERTIFICATION: {
        "certification_plan_id": "cert-plan-001",
        "compliance_items": 25,
        "compliant_items": 23,
        "verification_reports": 5,
    },
    PipelineStage.FLIGHT_TEST: {
        "flight_test_plan_id": "ftp-001",
        "test_subjects": 5,
        "estimated_flight_hours": 150,
        "test_points": 342,
    },
    PipelineStage.DELIVERY_PACKAGE: {
        "package_id": "pkg-001",
        "documents_count": 47,
        "total_size_mb": 2340,
        "validation_passed": True,
    },
}


class FullPipelineService:
    def __init__(self) -> None:
        self._runs: dict[str, FullPipelineRun] = {}

    def generate_full_delivery_package(
        self,
        tenant_id: str,
        project_id: str,
        aircraft_spec: dict[str, Any] | None = None,
        skip_stages: list[str] | None = None,
    ) -> FullPipelineRun:
        run = FullPipelineRun(
            tenant_id=tenant_id,
            project_id=project_id,
            aircraft_spec=aircraft_spec or {
                "aircraft_type": "light_transport",
                "mtow_kg": 5700,
                "passengers": 9,
                "range_nm": 1200,
                "engine_type": "turboprop",
            },
        )

        skip_set = set(skip_stages or [])

        for stage in PipelineStage:
            if stage.value in skip_set:
                run.skip_stage(stage)
                continue

            run.start_stage(stage)
            duration = random.uniform(2, 30)

            if random.random() < 0.95:
                output_data = _STAGE_OUTPUTS.get(stage, {})
                run.complete_stage(stage, output_data, duration)
            else:
                run.fail_stage(stage, "Simulated failure for testing")
                break

        if run.status != PipelineStatus.FAILED:
            run.complete_pipeline()

        self._runs[run.id] = run
        return run

    def get_pipeline_status(self, pipeline_id: str) -> FullPipelineRun | None:
        return self._runs.get(pipeline_id)

    def get_pipeline_report(self, pipeline_id: str) -> dict[str, Any] | None:
        run = self._runs.get(pipeline_id)
        if not run:
            return None

        progress = run.get_progress()
        stage_reports = []
        for stage, output in run.stage_outputs.items():
            stage_reports.append({
                "stage": stage.value,
                "description": _STAGE_DESCRIPTIONS.get(stage, ""),
                "status": output.status.value,
                "duration_seconds": output.duration_seconds,
                "output_summary": list(output.output_data.keys()) if output.output_data else [],
                "error": output.error_message,
            })

        issues = [
            {"stage": output.stage.value, "issue": output.error_message}
            for output in run.stage_outputs.values()
            if output.status == StageStatus.FAILED
        ]

        return {
            "pipeline_id": pipeline_id,
            "project_id": run.project_id,
            "status": run.status.value,
            "progress": progress,
            "stages": stage_reports,
            "issues": issues,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def retry_failed_stage(self, pipeline_id: str) -> FullPipelineRun | None:
        run = self._runs.get(pipeline_id)
        if not run or run.status != PipelineStatus.FAILED:
            return None

        for stage, output in run.stage_outputs.items():
            if output.status == StageStatus.FAILED:
                run.start_stage(stage)
                output_data = _STAGE_OUTPUTS.get(stage, {})
                run.complete_stage(stage, output_data, random.uniform(2, 15))
                break

        all_ok = all(
            o.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
            for o in run.stage_outputs.values()
        )
        if all_ok:
            run.complete_pipeline()

        return run

    def list_pipelines(self, tenant_id: str) -> list[FullPipelineRun]:
        return [r for r in self._runs.values() if r.tenant_id == tenant_id]