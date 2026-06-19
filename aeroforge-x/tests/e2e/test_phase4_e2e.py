"""
AeroForge-X Phase 4 End-to-End Tests
Covers: Digital Twin Fusion, MES Enhancement, Certification, Supply Chain, Knowledge, Ecosystem, Data Lake, Full Pipeline
"""
import pytest
from datetime import datetime, timezone


class TestDigitalTwinFusion:
    def test_create_unified_twin(self):
        from services.digital_twin_center.src.domain.entities.unified_twin import UnifiedTwin
        from services.digital_twin_center.src.domain.services.twin_fusion_domain_service import TwinFusionDomainService

        service = TwinFusionDomainService()
        twin = service.create_unified_twin(
            tenant_id="tenant-001",
            project_id="proj-001",
            aircraft_serial_number="AF-X100-001",
        )
        assert twin is not None
        assert twin.aircraft_serial_number == "AF-X100-001"
        assert twin.fusion_status == "partial_fusion"

    def test_fuse_twin_data(self):
        from services.digital_twin_center.src.domain.services.twin_fusion_domain_service import TwinFusionDomainService

        service = TwinFusionDomainService()
        twin = service.create_unified_twin("t1", "p1", "SN-001")
        result = service.fuse_twin_data(twin.id)
        assert result is not None
        assert result.fusion_status in ("partial_fusion", "full_fusion")

    def test_twin_loop_feedback(self):
        from services.digital_twin_center.src.domain.services.twin_loop_service import TwinLoopService

        service = TwinLoopService()
        report = service.feedback_flight_to_design("SN-001")
        assert report is not None

    def test_reduced_order_model(self):
        from services.digital_twin_center.src.domain.services.reduced_order_model_service import ReducedOrderModelService

        service = ReducedOrderModelService()
        rom = service.build_reduced_order_model("SN-001", "aerodynamic")
        assert rom is not None
        result = service.run_reduced_simulation(rom["rom_id"], {"alpha": 5.0})
        assert result is not None


class TestMESEnhancement:
    def test_adaptive_scheduling(self):
        from services.mes_center.src.domain.services.adaptive_scheduling_service import AdaptiveSchedulingService

        service = AdaptiveSchedulingService()
        schedule = service.create_adaptive_schedule("t1", "p1", "Test Schedule")
        assert schedule is not None
        assert schedule.name == "Test Schedule"

    def test_quality_prediction(self):
        from services.mes_center.src.domain.services.quality_prediction_service import QualityPredictionService
        from services.mes_center.src.domain.entities.quality_prediction import InputFeature, PredictionType

        service = QualityPredictionService()
        features = [
            InputFeature(name="forging_temperature", value=1150.0, unit="°C"),
            InputFeature(name="press_speed", value=50.0, unit="mm/s"),
        ]
        prediction = service.predict_quality("t1", "p1", "wo-001", PredictionType.OPERATION_QUALITY, features)
        assert prediction is not None
        assert prediction.predicted_result is not None

    def test_process_optimization(self):
        from services.mes_center.src.domain.services.process_optimization_service import ProcessOptimizationService

        service = ProcessOptimizationService()
        opt = service.analyze_process_bottleneck("t1", "p1", "route-001")
        assert opt is not None
        assert len(opt.bottleneck_analysis) > 0


class TestCertification:
    def test_create_certification_plan(self):
        from services.certification_center.src.domain.services.certification_plan_service import CertificationPlanService
        from services.certification_center.src.domain.entities.certification_plan import CertificationStandard, CertificationAuthority

        service = CertificationPlanService()
        plan = service.create_certification_plan(
            tenant_id="t1", project_id="p1", aircraft_type="AF-X100",
            certification_standard=CertificationStandard.FAR_25,
            certification_authority=CertificationAuthority.FAA,
        )
        assert plan is not None
        assert len(plan.compliance_items) > 0

    def test_compliance_verification(self):
        from services.certification_center.src.domain.services.compliance_verification_service import ComplianceVerificationService

        service = ComplianceVerificationService()
        report = service.verify_design_compliance("plan-001")
        assert report is not None
        assert report.compliant_count + report.non_compliant_count + report.needs_review_count > 0

    def test_airworthiness_approval(self):
        from services.certification_center.src.domain.services.airworthiness_service import AirworthinessService
        from services.certification_center.src.domain.entities.airworthiness_approval import ApprovalType

        service = AirworthinessService()
        approval = service.submit_approval_application("t1", "plan-001", ApprovalType.TYPE_CERTIFICATE)
        assert approval is not None
        assert approval.review_status.value == "submitted"

    def test_continuous_airworthiness(self):
        from services.certification_center.src.domain.services.continuous_airworthiness_service import ContinuousAirworthinessService

        service = ContinuousAirworthinessService()
        record = service.create_record("t1", "SN-001")
        assert record is not None

        service.import_airworthiness_directive("SN-001", "AD-2026-001", "Wing inspection", "2026-01-01", "2026-06-30")
        assessment = service.assess_overall_airworthiness("SN-001")
        assert assessment is not None


class TestSupplyChain:
    def test_supplier_network(self):
        from services.supply_chain.src.domain.services.supplier_collaboration_service import SupplierCollaborationService

        service = SupplierCollaborationService()
        network = service.build_supplier_network("t1", "p1")
        assert network is not None
        assert len(network.nodes) > 0

    def test_supply_risk(self):
        from services.supply_chain.src.domain.services.supply_risk_service import SupplyRiskService

        service = SupplyRiskService()
        alerts = service.monitor_supply_risks("t1", "net-001")
        assert isinstance(alerts, list)

    def test_smart_purchase(self):
        from services.supply_chain.src.domain.services.smart_purchase_service import SmartPurchaseService

        service = SmartPurchaseService()
        order = service.generate_smart_purchase_order("t1", "p1")
        assert order is not None
        assert len(order["order_lines"]) > 0


class TestKnowledge:
    def test_knowledge_graph(self):
        from services.knowledge_center.src.domain.services.knowledge_graph_service import KnowledgeGraphService

        service = KnowledgeGraphService()
        entities = service.ingest_regulation_knowledge("t1")
        assert len(entities) > 0

        materials = service.ingest_material_knowledge("t1")
        assert len(materials) > 0

        result = service.build_knowledge_graph("t1")
        assert result["total_entities"] > 0

    def test_recommendations(self):
        from services.knowledge_center.src.domain.services.decision_support_service import IntelligentRecommendationService

        service = IntelligentRecommendationService()
        rec = service.recommend_design_parameters("t1", "p1")
        assert rec is not None
        assert len(rec["recommendations"]) > 0

    def test_decision_support(self):
        from services.knowledge_center.src.domain.services.decision_support_service import DecisionSupportService

        service = DecisionSupportService()
        result = service.support_design_decision("t1", "p1")
        assert result is not None
        assert len(result["alternatives_comparison"]) > 0


class TestEcosystem:
    def test_developer_portal(self):
        from services.platform_ecosystem.src.domain.services.ecosystem_services import DeveloperPortalService

        service = DeveloperPortalService()
        dev = service.register_developer("t1", "Test Dev", "dev@test.com")
        assert dev is not None

        key = service.create_api_key(dev["developer_id"])
        assert key is not None

    def test_plugin_marketplace(self):
        from services.platform_ecosystem.src.domain.services.ecosystem_services import PluginMarketplaceService

        service = PluginMarketplaceService()
        plugin = service.submit_plugin("t1", "dev-001", "Test Plugin", "A test plugin", "visualization")
        assert plugin is not None

        service.review_and_publish(plugin.id)
        plugins = service.list_plugins()
        assert len(plugins) > 0


class TestDataLake:
    def test_data_ingestion(self):
        from services.data_lake.src.domain.services.data_lake_service import DataLakeService
        from services.data_lake.src.domain.entities.data_lake_job import DataSource

        service = DataLakeService()
        job = service.ingest_data("t1", DataSource.MES)
        assert job is not None
        assert job.records_processed > 0

    def test_ai_training(self):
        from services.data_lake.src.domain.services.data_lake_service import AITrainingPlatformService

        service = AITrainingPlatformService()
        dataset = service.create_dataset("t1", "Test Dataset")
        assert dataset is not None

        training = service.start_training("t1", dataset.id)
        assert training is not None
        assert training.metrics.get("accuracy", 0) > 0


class TestFullPipeline:
    def test_full_pipeline_generation(self):
        from services.delivery_center.src.domain.services.full_pipeline_service import FullPipelineService

        service = FullPipelineService()
        run = service.generate_full_delivery_package("t1", "p1")
        assert run is not None
        assert run.status.value in ("completed", "failed")

        progress = run.get_progress()
        assert progress["total_stages"] == 8

        report = service.get_pipeline_report(run.id)
        assert report is not None
        assert len(report["stages"]) == 8