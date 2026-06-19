from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code


class InspectionPlan:
    def __init__(
        self,
        inspection_type: str,
        item_code: str,
        work_order_id: str | None = None,
    ) -> None:
        self.id = generate_code("IPL")
        self.plan_code: str = generate_code(f"IQC" if inspection_type == "iqc" else "FQC")
        self.inspection_type = inspection_type
        self.item_code = item_code
        self.items: list[dict[str, Any]] = self._default_items(inspection_type)
        self.status: str = "pending"
        self.work_order_id = work_order_id
        self.created_at: datetime = datetime.now(timezone.utc)

    def _default_items(self, inspection_type: str) -> list[dict[str, Any]]:
        if inspection_type == "iqc":
            return [
                {"name": "外观检查", "method": "目视", "criteria": "无划痕、无变形、无色差"},
                {"name": "尺寸测量", "method": "三坐标测量", "criteria": "关键尺寸公差±0.1mm"},
                {"name": "材料证明核对", "method": "文件审查", "criteria": "材料合格证、批次号一致"},
                {"name": "合格证核对", "method": "文件审查", "criteria": "供应商合格证齐全"},
            ]
        elif inspection_type == "fqc":
            return [
                {"name": "全尺寸检测", "method": "三坐标测量", "criteria": "所有尺寸符合图纸要求"},
                {"name": "功能测试", "method": "功能测试台", "criteria": "功能正常、无异常"},
                {"name": "外观终检", "method": "目视", "criteria": "表面质量达标"},
            ]
        return []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_code": self.plan_code,
            "inspection_type": self.inspection_type,
            "item_code": self.item_code,
            "items": self.items,
            "status": self.status,
            "work_order_id": self.work_order_id,
            "created_at": self.created_at.isoformat(),
        }


class InspectionRecord:
    RESULT_PASS = "pass"
    RESULT_FAIL = "fail"
    RESULT_MARGINAL = "marginal"

    def __init__(
        self,
        inspection_type: str,
        item_code: str,
        plan_id: str | None = None,
        inspector: str = "",
    ) -> None:
        self.id = generate_code("IREC")
        self.record_code: str = generate_code("REC")
        self.inspection_type = inspection_type
        self.plan_id = plan_id
        self.item_code = item_code
        self.result: str = ""
        self.inspector = inspector
        self.inspection_date: datetime = datetime.now(timezone.utc)
        self.criteria: dict[str, Any] = {}
        self.measurements: dict[str, Any] = {}
        self.notes: str = ""
        self.created_at: datetime = datetime.now(timezone.utc)

    def judge_result(self, measurements: dict[str, Any], criteria: dict[str, Any]) -> str:
        self.measurements = measurements
        self.criteria = criteria
        all_pass = True
        has_marginal = False
        for key, spec_value in criteria.items():
            measured = measurements.get(key)
            if measured is None:
                all_pass = False
                continue
            if isinstance(spec_value, (int, float)) and isinstance(measured, (int, float)):
                tolerance = abs(spec_value) * 0.05
                if abs(measured - spec_value) > tolerance * 2:
                    all_pass = False
                elif abs(measured - spec_value) > tolerance:
                    has_marginal = True
        if not all_pass:
            self.result = self.RESULT_FAIL
        elif has_marginal:
            self.result = self.RESULT_MARGINAL
        else:
            self.result = self.RESULT_PASS
        return self.result

    def is_pass(self) -> bool:
        return self.result == self.RESULT_PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "record_code": self.record_code,
            "inspection_type": self.inspection_type,
            "plan_id": self.plan_id,
            "item_code": self.item_code,
            "result": self.result,
            "inspector": self.inspector,
            "inspection_date": self.inspection_date.isoformat(),
            "criteria": self.criteria,
            "measurements": self.measurements,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


class CAPA:
    STATUS_OPEN = "open"
    STATUS_EXECUTING = "executing"
    STATUS_VERIFYING = "verifying"
    STATUS_CLOSED = "closed"

    def __init__(
        self,
        inspection_record_id: str | None = None,
        created_by: str = "",
    ) -> None:
        self.id = generate_code("CAPA")
        self.capa_code: str = generate_code("CAP")
        self.root_cause: str = ""
        self.corrective_action: str = ""
        self.preventive_action: str = ""
        self.verification_result: str = ""
        self.status: str = self.STATUS_OPEN
        self.due_date: datetime | None = None
        self.escalated: bool = False
        self.inspection_record_id = inspection_record_id
        self.created_by = created_by
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def execute(self, root_cause: str, corrective_action: str, preventive_action: str) -> None:
        if self.status != self.STATUS_OPEN:
            raise ValueError(f"Cannot execute CAPA in status '{self.status}'")
        self.root_cause = root_cause
        self.corrective_action = corrective_action
        self.preventive_action = preventive_action
        self.status = self.STATUS_EXECUTING
        self.updated_at = datetime.now(timezone.utc)

    def verify(self, result: str) -> None:
        if self.status != self.STATUS_VERIFYING and self.status != self.STATUS_EXECUTING:
            raise ValueError(f"Cannot verify CAPA in status '{self.status}'")
        self.verification_result = result
        self.status = self.STATUS_VERIFYING if result == "marginal" else self.STATUS_CLOSED
        self.updated_at = datetime.now(timezone.utc)

    def check_overdue(self) -> bool:
        if self.status == self.STATUS_CLOSED:
            return False
        if self.due_date and datetime.now(timezone.utc) > self.due_date:
            self.escalated = True
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "capa_code": self.capa_code,
            "root_cause": self.root_cause,
            "corrective_action": self.corrective_action,
            "preventive_action": self.preventive_action,
            "verification_result": self.verification_result,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "escalated": self.escalated,
            "inspection_record_id": self.inspection_record_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }