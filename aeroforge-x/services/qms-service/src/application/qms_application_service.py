from __future__ import annotations

from typing import Any

from ..domain.entities.qms_entities import CAPA, InspectionPlan, InspectionRecord
from ..domain.services.qms_domain_service import QmsDomainService
from ..infrastructure.qms_repository import QmsRepository


class QmsApplicationService:
    def __init__(self, repo: QmsRepository) -> None:
        self._repo = repo
        self._domain_service = QmsDomainService()

    async def generate_iqc_plan(self, item_code: str, work_order_id: str | None = None) -> dict[str, Any]:
        plan = self._domain_service.generate_iqc_plan(item_code, work_order_id)
        await self._repo.save_plan(plan.to_dict())
        return plan.to_dict()

    async def generate_fqc_plan(self, item_code: str, work_order_id: str | None = None) -> dict[str, Any]:
        plan = self._domain_service.generate_fqc_plan(item_code, work_order_id)
        await self._repo.save_plan(plan.to_dict())
        return plan.to_dict()

    async def record_iqc_result(
        self, item_code: str, inspector: str, measurements: dict[str, Any], criteria: dict[str, Any], plan_id: str | None = None
    ) -> dict[str, Any]:
        record = self._domain_service.record_inspection_result("iqc", item_code, inspector, measurements, criteria, plan_id)
        await self._repo.save_record(record.to_dict())
        event_type = "inspection.completed"
        return {
            "record": record.to_dict(),
            "material_released": self._domain_service.is_material_released(record),
            "event_type": event_type,
        }

    async def record_fqc_result(
        self, item_code: str, inspector: str, measurements: dict[str, Any], criteria: dict[str, Any], plan_id: str | None = None
    ) -> dict[str, Any]:
        record = self._domain_service.record_inspection_result("fqc", item_code, inspector, measurements, criteria, plan_id)
        await self._repo.save_record(record.to_dict())
        return {"record": record.to_dict(), "material_released": record.is_pass()}

    async def create_capa(self, inspection_record_id: str | None = None, created_by: str = "") -> dict[str, Any]:
        capa = self._domain_service.create_capa(inspection_record_id, created_by)
        await self._repo.save_capa(capa.to_dict())
        return capa.to_dict()

    async def execute_capa(self, capa_id: str, root_cause: str, corrective_action: str, preventive_action: str) -> dict[str, Any] | None:
        capa_data = await self._repo.find_capa_by_id(capa_id)
        if capa_data is None:
            return None
        capa = self._reconstruct_capa(capa_data)
        self._domain_service.execute_capa(capa, root_cause, corrective_action, preventive_action)
        await self._repo.save_capa(capa.to_dict())
        return capa.to_dict()

    async def verify_capa(self, capa_id: str, result: str) -> dict[str, Any] | None:
        capa_data = await self._repo.find_capa_by_id(capa_id)
        if capa_data is None:
            return None
        capa = self._reconstruct_capa(capa_data)
        self._domain_service.verify_capa(capa, result)
        await self._repo.save_capa(capa.to_dict())
        return capa.to_dict()

    async def check_iqc_status(self, item_code: str) -> dict[str, Any]:
        record = await self._repo.find_latest_iqc_for_item(item_code)
        if record is None:
            return {"item_code": item_code, "iqc_status": "not_inspected", "material_released": False}
        return {"item_code": item_code, "iqc_status": record.get("result", ""), "material_released": record.get("result") == "pass"}

    def _reconstruct_capa(self, data: dict[str, Any]) -> CAPA:
        capa = CAPA(inspection_record_id=data.get("inspection_record_id"), created_by=data.get("created_by", ""))
        capa.id = data["id"]
        capa.capa_code = data["capa_code"]
        capa.root_cause = data.get("root_cause", "")
        capa.corrective_action = data.get("corrective_action", "")
        capa.preventive_action = data.get("preventive_action", "")
        capa.verification_result = data.get("verification_result", "")
        capa.status = data.get("status", "open")
        capa.escalated = data.get("escalated", False)
        return capa