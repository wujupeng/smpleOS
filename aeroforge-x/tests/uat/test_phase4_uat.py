"""
AeroForge-X Phase 4 User Acceptance Tests
"""
import pytest


class TestPhase4UAT:
    def test_uat_digital_twin_fusion_workflow(self):
        from services.digital_twin_center.src.domain.services.twin_fusion_domain_service import TwinFusionDomainService
        from services.digital_twin_center.src.domain.services.twin_loop_service import TwinLoopService

        fusion_svc = TwinFusionDomainService()
        loop_svc = TwinLoopService()

        twin = fusion_svc.create_unified_twin("t1", "p1", "SN-UAT-001")
        assert twin.fusion_status == "partial_fusion"

        fused = fusion_svc.fuse_twin_data(twin.id)
        assert fused.fusion_status in ("partial_fusion", "full_fusion")

        insights = fusion_svc.detect_cross_twin_anomaly(twin.id)
        assert isinstance(insights, list)

        report = loop_svc.generate_loop_report("SN-UAT-001")
        assert report is not None

    def test_uat_mes_enhancement_workflow(self):
        from services.mes_center.src.domain.services.adaptive_scheduling_service import AdaptiveSchedulingService
        from services.mes_center.src.domain.services.quality_prediction_service import QualityPredictionService
        from services.mes_center.src.domain.services.process_optimization_service import ProcessOptimizationService
        from services.mes_center.src.domain.entities.quality_prediction import InputFeature, PredictionType

        schedule_svc = AdaptiveSchedulingService()
        quality_svc = QualityPredictionService()
        process_svc = ProcessOptimizationService()

        schedule = schedule_svc.create_adaptive_schedule("t1", "p1", "UAT Schedule")
        assert schedule is not None

        features = [InputFeature(name="temp", value=1150.0, unit="°C")]
        prediction = quality_svc.predict_quality("t1", "p1", "wo-uat", PredictionType.OPERATION_QUALITY, features)
        assert prediction.predicted_result is not None

        drivers = quality_svc.identify_quality_drivers(prediction.id)
        assert len(drivers) > 0

        opt = process_svc.analyze_process_bottleneck("t1", "p1", "route-uat")
        assert len(opt.bottleneck_analysis) > 0

    def test_uat_certification_workflow(self):
        from services.certification_center.src.domain.services.certification_plan_service import CertificationPlanService
        from services.certification_center.src.domain.services.compliance_verification_service import ComplianceVerificationService
        from services.certification_center.src.domain.services.airworthiness_service import AirworthinessService
        from services.certification_center.src.domain.entities.certification_plan import CertificationStandard, CertificationAuthority, ItemStatus
        from services.certification_center.src.domain.entities.airworthiness_approval import ApprovalType

        plan_svc = CertificationPlanService()
        verify_svc = ComplianceVerificationService()
        air_svc = AirworthinessService()

        plan = plan_svc.create_certification_plan("t1", "p1", "AF-X100", CertificationStandard.FAR_25, CertificationAuthority.FAA)
        assert len(plan.compliance_items) > 0

        design_report = verify_svc.verify_design_compliance(plan.id)
        assert design_report is not None

        progress = plan_svc.track_compliance_progress(plan.id)
        assert progress is not None

        approval = air_svc.submit_approval_application("t1", plan.id, ApprovalType.TYPE_CERTIFICATE)
        assert approval is not None

    def test_uat_supply_chain_workflow(self):
        from services.supply_chain.src.domain.services.supplier_collaboration_service import SupplierCollaborationService
        from services.supply_chain.src.domain.services.supply_risk_service import SupplyRiskService
        from services.supply_chain.src.domain.services.smart_purchase_service import SmartPurchaseService

        collab_svc = SupplierCollaborationService()
        risk_svc = SupplyRiskService()
        purchase_svc = SmartPurchaseService()

        network = collab_svc.build_supplier_network("t1", "p1")
        assert len(network.nodes) > 0

        forecast = collab_svc.share_demand_forecast(network.id)
        assert forecast is not None

        order = purchase_svc.generate_smart_purchase_order("t1", "p1")
        assert order is not None

    def test_uat_knowledge_and_decision_workflow(self):
        from services.knowledge_center.src.domain.services.knowledge_graph_service import KnowledgeGraphService
        from services.knowledge_center.src.domain.services.decision_support_service import IntelligentRecommendationService, DecisionSupportService

        kg_svc = KnowledgeGraphService()
        rec_svc = IntelligentRecommendationService()
        dec_svc = DecisionSupportService()

        kg_svc.ingest_regulation_knowledge("t1")
        kg_svc.ingest_material_knowledge("t1")
        result = kg_svc.build_knowledge_graph("t1")
        assert result["total_entities"] > 0

        query_results = kg_svc.query_knowledge_graph("t1", "titanium")
        assert len(query_results) > 0

        rec = rec_svc.recommend_material_selection("t1", "p1")
        assert len(rec["materials"]) > 0

        decision = dec_svc.support_make_or_buy_decision("t1", "p1")
        assert "recommendation" in decision

    def test_uat_full_pipeline_workflow(self):
        from services.delivery_center.src.domain.services.full_pipeline_service import FullPipelineService

        service = FullPipelineService()
        run = service.generate_full_delivery_package("t1", "p1", {
            "aircraft_type": "light_transport",
            "mtow_kg": 5700,
            "passengers": 9,
        })

        assert run.status.value in ("completed", "failed")
        progress = run.get_progress()
        assert progress["total_stages"] == 8

        report = service.get_pipeline_report(run.id)
        assert len(report["stages"]) == 8

        if run.status.value == "failed":
            retried = service.retry_failed_stage(run.id)
            assert retried is not None