import pytest

from services.qms_service.src.domain.entities.qms_entities import CAPA, InspectionPlan, InspectionRecord
from services.qms_service.src.domain.services.qms_domain_service import QmsDomainService
from services.trace_service.src.domain.services.material_trace_domain_service import MaterialTraceDomainService


class TestInspectionPlan:
    def test_generate_iqc_plan(self) -> None:
        plan = InspectionPlan(inspection_type="iqc", item_code="AAF-SPAR-001")
        assert plan.inspection_type == "iqc"
        assert len(plan.items) == 4
        assert plan.items[0]["name"] == "外观检查"

    def test_generate_fqc_plan(self) -> None:
        plan = InspectionPlan(inspection_type="fqc", item_code="AAF-001")
        assert plan.inspection_type == "fqc"
        assert len(plan.items) == 3
        assert plan.items[0]["name"] == "全尺寸检测"


class TestInspectionRecord:
    def test_judge_result_pass(self) -> None:
        record = InspectionRecord(inspection_type="iqc", item_code="AAF-001", inspector="张工")
        result = record.judge_result(
            measurements={"dimension": 10.02, "weight": 2.31},
            criteria={"dimension": 10.0, "weight": 2.3},
        )
        assert result == "pass"
        assert record.is_pass()

    def test_judge_result_fail(self) -> None:
        record = InspectionRecord(inspection_type="iqc", item_code="AAF-001", inspector="张工")
        result = record.judge_result(
            measurements={"dimension": 12.0, "weight": 2.3},
            criteria={"dimension": 10.0, "weight": 2.3},
        )
        assert result == "fail"
        assert not record.is_pass()

    def test_judge_result_marginal(self) -> None:
        record = InspectionRecord(inspection_type="iqc", item_code="AAF-001", inspector="张工")
        result = record.judge_result(
            measurements={"dimension": 10.08},
            criteria={"dimension": 10.0},
        )
        assert result == "marginal"


class TestCAPA:
    def test_create_capa(self) -> None:
        capa = CAPA(inspection_record_id="rec-1", created_by="quality_eng")
        assert capa.status == "open"
        assert capa.capa_code.startswith("CAP-")

    def test_execute_capa(self) -> None:
        capa = CAPA(created_by="quality_eng")
        capa.execute(
            root_cause="材料批次不合格",
            corrective_action="更换供应商",
            preventive_action="加强来料检验",
        )
        assert capa.status == "executing"
        assert capa.root_cause == "材料批次不合格"

    def test_verify_capa_pass(self) -> None:
        capa = CAPA(created_by="quality_eng")
        capa.execute("根因", "纠正", "预防")
        capa.verify("pass")
        assert capa.status == "closed"

    def test_verify_capa_marginal(self) -> None:
        capa = CAPA(created_by="quality_eng")
        capa.execute("根因", "纠正", "预防")
        capa.verify("marginal")
        assert capa.status == "verifying"

    def test_cannot_execute_closed_capa(self) -> None:
        capa = CAPA(created_by="quality_eng")
        capa.execute("根因", "纠正", "预防")
        capa.verify("pass")
        with pytest.raises(ValueError, match="Cannot execute"):
            capa.execute("新根因", "新纠正", "新预防")

    def test_check_overdue(self) -> None:
        from datetime import datetime, timedelta, timezone
        capa = CAPA(created_by="quality_eng")
        capa.due_date = datetime.now(timezone.utc) - timedelta(days=1)
        assert capa.check_overdue() is True
        assert capa.escalated is True


class TestQmsDomainService:
    def test_generate_iqc_plan(self) -> None:
        service = QmsDomainService()
        plan = service.generate_iqc_plan("AAF-001", "wo-1")
        assert plan.inspection_type == "iqc"
        assert plan.work_order_id == "wo-1"

    def test_record_inspection_and_check_release(self) -> None:
        service = QmsDomainService()
        record = service.record_inspection_result(
            "iqc", "AAF-001", "张工",
            {"dimension": 10.0}, {"dimension": 10.0},
        )
        assert record.is_pass()
        assert service.is_material_released(record) is True

    def test_iqc_fail_blocks_material(self) -> None:
        service = QmsDomainService()
        record = service.record_inspection_result(
            "iqc", "AAF-001", "张工",
            {"dimension": 15.0}, {"dimension": 10.0},
        )
        assert not record.is_pass()
        assert service.is_material_released(record) is False

    def test_capa_full_flow(self) -> None:
        service = QmsDomainService()
        capa = service.create_capa("rec-1", "quality_eng")
        service.execute_capa(capa, "根因分析", "纠正措施", "预防措施")
        service.verify_capa(capa, "pass")
        assert capa.status == "closed"