"""
AeroForge-X Phase 4 Performance Tests
"""
import pytest
import time


class TestPhase4Performance:
    def test_twin_fusion_performance(self):
        from services.digital_twin_center.src.domain.services.twin_fusion_domain_service import TwinFusionDomainService

        service = TwinFusionDomainService()
        start = time.time()
        for _ in range(100):
            twin = service.create_unified_twin("t1", "p1", f"SN-{_}")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"100 twin creations took {elapsed:.2f}s"

    def test_quality_prediction_performance(self):
        from services.mes_center.src.domain.services.quality_prediction_service import QualityPredictionService
        from services.mes_center.src.domain.entities.quality_prediction import InputFeature, PredictionType

        service = QualityPredictionService()
        features = [InputFeature(name=f"param_{i}", value=float(i * 10)) for i in range(10)]

        start = time.time()
        for _ in range(100):
            service.predict_quality("t1", "p1", f"wo-{_}", PredictionType.OPERATION_QUALITY, features)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"100 predictions took {elapsed:.2f}s"

    def test_certification_plan_performance(self):
        from services.certification_center.src.domain.services.certification_plan_service import CertificationPlanService
        from services.certification_center.src.domain.entities.certification_plan import CertificationStandard, CertificationAuthority

        service = CertificationPlanService()
        start = time.time()
        for _ in range(50):
            service.create_certification_plan(
                "t1", f"p-{_}", "AF-X100",
                CertificationStandard.FAR_25, CertificationAuthority.FAA,
            )
        elapsed = time.time() - start
        assert elapsed < 3.0, f"50 plan creations took {elapsed:.2f}s"

    def test_knowledge_graph_query_performance(self):
        from services.knowledge_center.src.domain.services.knowledge_graph_service import KnowledgeGraphService

        service = KnowledgeGraphService()
        service.ingest_regulation_knowledge("t1")
        service.ingest_material_knowledge("t1")
        service.build_knowledge_graph("t1")

        start = time.time()
        for _ in range(100):
            service.query_knowledge_graph("t1", "titanium")
        elapsed = time.time() - start
        assert elapsed < 3.0, f"100 queries took {elapsed:.2f}s"

    def test_full_pipeline_performance(self):
        from services.delivery_center.src.domain.services.full_pipeline_service import FullPipelineService

        service = FullPipelineService()
        start = time.time()
        run = service.generate_full_delivery_package("t1", "p1")
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Full pipeline took {elapsed:.2f}s"
        assert run.status.value in ("completed", "failed")