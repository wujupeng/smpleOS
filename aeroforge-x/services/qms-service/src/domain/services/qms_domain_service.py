from __future__ import annotations

from typing import Any

from ..entities.qms_entities import CAPA, InspectionPlan, InspectionRecord


class QmsDomainService:
    def generate_iqc_plan(self, item_code: str, work_order_id: str | None = None) -> InspectionPlan:
        return InspectionPlan(inspection_type="iqc", item_code=item_code, work_order_id=work_order_id)

    def generate_fqc_plan(self, item_code: str, work_order_id: str | None = None) -> InspectionPlan:
        return InspectionPlan(inspection_type="fqc", item_code=item_code, work_order_id=work_order_id)

    def record_inspection_result(
        self,
        inspection_type: str,
        item_code: str,
        inspector: str,
        measurements: dict[str, Any],
        criteria: dict[str, Any],
        plan_id: str | None = None,
    ) -> InspectionRecord:
        record = InspectionRecord(inspection_type=inspection_type, item_code=item_code, plan_id=plan_id, inspector=inspector)
        record.judge_result(measurements, criteria)
        return record

    def is_material_released(self, record: InspectionRecord) -> bool:
        if record.inspection_type == "iqc":
            return record.is_pass()
        return True

    def create_capa(self, inspection_record_id: str | None = None, created_by: str = "") -> CAPA:
        return CAPA(inspection_record_id=inspection_record_id, created_by=created_by)

    def execute_capa(self, capa: CAPA, root_cause: str, corrective_action: str, preventive_action: str) -> None:
        capa.execute(root_cause, corrective_action, preventive_action)

    def verify_capa(self, capa: CAPA, result: str) -> None:
        capa.verify(result)