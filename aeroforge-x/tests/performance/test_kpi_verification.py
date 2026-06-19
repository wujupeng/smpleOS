"""AeroForge-X V6.1 Performance Tests - V6.0 Key Performance Indicators
V61-PERF3: Configuration propagation <10s, Checklist generation <30s,
Evidence assembly <60s, UQ inference <10ms, Shop floor latency <500ms
REQ-VP-063~068
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.configuration_management.configuration_manager_service import ConfigurationManagerService
from src.domain.services.configuration_management.three_view_config_propagation_service import (
    ThreeViewConfigPropagationService, ManufacturingRule, OperationalRule, DesignConfigChange,
)
from src.domain.services.certification.regulatory_library_service import RegulatoryLibraryService, RegulationType
from src.domain.services.certification.compliance_checklist_service import ComplianceChecklistService
from src.domain.services.certification.certification_evidence_assembly_service import (
    CertificationEvidenceAssemblyService, EvidenceItem, EvidenceType, EvidenceVerificationStatus,
)
from src.domain.services.generative_design.uncertainty_quantification_service import (
    UncertaintyQuantificationService, UQMethodType, UQMethodSpec,
)
from src.domain.services.digital_factory.shop_floor_data_collector_service import (
    ShopFloorDataCollectorService, EquipmentRegistration, EquipmentType,
    Protocol, ShopFloorDataPoint, OPCUAConfig,
)


class TestConfigPropagationKPI:

    def test_three_view_propagation_under_10s(self):
        config_mgr = ConfigurationManagerService()
        propagation = ThreeViewConfigPropagationService()
        propagation.registerManufacturingRule(
            ManufacturingRule(rule_id="MR-1", rule_type="ProcessAssignment", rule_expression="CNC", priority=1)
        )
        propagation.registerOperationalRule(
            OperationalRule(rule_id="OR-1", rule_type="EquipmentInstallation", rule_expression="BAY-1", priority=1)
        )
        block = config_mgr.createBlockConfig("A320", "Block-1")

        change = DesignConfigChange(
            block_id=block.block_id,
            changed_items=[{"item_id": block.design_config.configuration_items[0].item_id, "new_values": {"x": 1}}],
            change_reason="KPI test",
        )
        start = time.monotonic()
        result = propagation.propagateDesignChange(block, change)
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.design_updated is True
        assert elapsed < 10000, f"Three-view propagation took {elapsed:.1f}ms > 10000ms"


class TestChecklistGenerationKPI:

    def test_checklist_generation_under_30s(self):
        reg_svc = RegulatoryLibraryService()
        checklist_svc = ComplianceChecklistService()

        start = time.monotonic()
        lib = reg_svc.importRegulation(RegulationType.FAA_PART_25, "FAA Part 25", "Amdt-1")
        checklist = checklist_svc.generateChecklist(lib, "PROJ-001")
        elapsed = (time.monotonic() - start) * 1000.0

        assert len(checklist.items) > 0
        assert elapsed < 30000, f"Checklist generation took {elapsed:.1f}ms > 30000ms"


class TestEvidenceAssemblyKPI:

    def test_evidence_assembly_under_60s(self):
        reg_svc = RegulatoryLibraryService()
        checklist_svc = ComplianceChecklistService()
        evidence_svc = CertificationEvidenceAssemblyService()

        lib = reg_svc.importRegulation(RegulationType.FAA_PART_25, "FAA Part 25", "Amdt-1")
        checklist = checklist_svc.generateChecklist(lib, "PROJ-001")

        evidence_items = [
            EvidenceItem(
                evidence_id=f"EVD-{i}",
                evidence_type=EvidenceType.TEST_REPORT,
                document_ref=f"DOC-{i}",
                verification_status=EvidenceVerificationStatus.VERIFIED,
                regulation_section=item.regulation_reference,
            )
            for i, item in enumerate(checklist.items)
        ]

        start = time.monotonic()
        pkg = evidence_svc.assembleEvidencePackage(checklist.checklist_id, "PROJ-001", evidence_items)
        required = [item.regulation_reference for item in checklist.items]
        validation = evidence_svc.validatePackageCompleteness(pkg.package_id, required)
        locked = evidence_svc.lockEvidencePackage(pkg.package_id)
        elapsed = (time.monotonic() - start) * 1000.0

        assert locked.is_locked is True
        assert elapsed < 60000, f"Evidence assembly took {elapsed:.1f}ms > 60000ms"


class TestUQInferenceKPI:

    def test_uq_inference_under_10ms(self):
        uq_svc = UncertaintyQuantificationService()
        spec = UQMethodSpec(
            method_id="UQ-EN-001", method_type=UQMethodType.ENSEMBLE,
            hyperparameters={"num_models": 5, "seeds": [1, 2, 3, 4, 5]},
        )
        uq_svc.registerUQMethod(spec)

        start = time.monotonic()
        result = uq_svc.predictWithUQ({"CL": 0.5}, method="UQ-EN-001")
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.uq_method == "Ensemble"
        assert elapsed < 10, f"UQ inference took {elapsed:.1f}ms > 10ms"


class TestShopFloorLatencyKPI:

    def test_data_quality_validation_under_500ms(self):
        collector = ShopFloorDataCollectorService()
        eq = EquipmentRegistration(
            equipment_id="EQ-001", equipment_name="CNC",
            equipment_type=EquipmentType.CNC, protocol=Protocol.OPC_UA,
        )
        collector.registerEquipment(eq)
        collector.startOPCUACollection("EQ-001", OPCUAConfig(server_url="opc.tcp://localhost:4840"))

        dp = ShopFloorDataPoint(
            timestamp=1000.0, equipment_id="EQ-001",
            data_type="Temperature", value=150.0, unit="C",
        )

        start = time.monotonic()
        result = collector.validateDataQuality(dp)
        elapsed = (time.monotonic() - start) * 1000.0

        assert result.is_valid is True
        assert elapsed < 500, f"Data quality validation took {elapsed:.1f}ms > 500ms"