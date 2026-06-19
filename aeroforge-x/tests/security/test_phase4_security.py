"""
AeroForge-X Phase 4 Security Audit Tests
"""
import pytest


class TestPhase4Security:
    def test_tenant_isolation_in_twin(self):
        from services.digital_twin_center.src.domain.services.twin_fusion_domain_service import TwinFusionDomainService

        service = TwinFusionDomainService()
        twin_a = service.create_unified_twin("tenant-A", "p1", "SN-001")
        twin_b = service.create_unified_twin("tenant-B", "p1", "SN-002")
        assert twin_a.tenant_id != twin_b.tenant_id
        assert twin_a.id != twin_b.id

    def test_certification_data_integrity(self):
        from services.certification_center.src.domain.services.certification_plan_service import CertificationPlanService
        from services.certification_center.src.domain.entities.certification_plan import CertificationStandard, CertificationAuthority, ItemStatus

        service = CertificationPlanService()
        plan = service.create_certification_plan("t1", "p1", "AF-X100", CertificationStandard.FAR_25, CertificationAuthority.FAA)
        original_count = len(plan.compliance_items)

        service.update_item_status(plan.id, plan.compliance_items[0].item_id, ItemStatus.COMPLIANT)
        updated = service.get_plan(plan.id)
        assert len(updated.compliance_items) == original_count

    def test_api_key_scoping(self):
        from services.platform_ecosystem.src.domain.services.ecosystem_services import DeveloperPortalService

        service = DeveloperPortalService()
        dev = service.register_developer("t1", "Dev", "dev@test.com")
        key = service.create_api_key(dev["developer_id"], scopes=["read"], rate_limit=100)
        assert "read" in key.scopes
        assert "write" not in key.scopes
        assert key.rate_limit == 100

    def test_data_lake_access_control(self):
        from services.data_lake.src.domain.services.data_lake_service import DataLakeService
        from services.data_lake.src.domain.entities.data_lake_job import DataSource

        service = DataLakeService()
        job = service.ingest_data("tenant-A", DataSource.MES)
        assert job.tenant_id == "tenant-A"

        tenant_b_jobs = service.list_jobs("tenant-B")
        assert job.id not in [j.id for j in tenant_b_jobs]

    def test_no_secrets_in_output(self):
        from services.mes_center.src.domain.services.quality_prediction_service import QualityPredictionService
        from services.mes_center.src.domain.entities.quality_prediction import InputFeature, PredictionType

        service = QualityPredictionService()
        features = [InputFeature(name="temp", value=100.0)]
        prediction = service.predict_quality("t1", "p1", "wo-001", PredictionType.OPERATION_QUALITY, features)
        output = prediction.to_detail_dict()
        output_str = str(output)
        sensitive_keywords = ["password", "secret", "token", "credential", "api_key"]
        for kw in sensitive_keywords:
            assert kw not in output_str.lower(), f"Sensitive keyword '{kw}' found in output"

    def test_pipeline_data_validation(self):
        from services.delivery_center.src.domain.services.full_pipeline_service import FullPipelineService

        service = FullPipelineService()
        run = service.generate_full_delivery_package("t1", "p1")
        for stage, output in run.stage_outputs.items():
            if output.status.value == "completed":
                assert isinstance(output.output_data, dict)
                assert output.duration_seconds >= 0