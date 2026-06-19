"""AeroForge-X V6.1 Integration Tests - Shared Fixtures

Provides common fixtures for all integration tests:
- sys.path setup for 3 services
- Domain service instances (lazy singletons)
- Cross-program event orchestrator
"""

import sys
import os

_SERVICES_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "services")
for _svc in ["aircraft-core-service", "physics-twin-service", "workflow-engine-service"]:
    _path = os.path.join(_SERVICES_ROOT, _svc)
    if _path not in sys.path:
        sys.path.insert(0, _path)

import pytest

from src.domain.services.configuration_management.configuration_manager_service import ConfigurationManagerService
from src.domain.services.configuration_management.three_view_config_propagation_service import ThreeViewConfigPropagationService
from src.domain.services.configuration_management.configuration_baseline_service import ConfigurationBaselineService
from src.domain.services.configuration_management.configuration_change_control_service import ConfigurationChangeControlService
from src.domain.services.certification.requirements_traceability_service import RequirementsTraceabilityService
from src.domain.services.certification.regulatory_library_service import RegulatoryLibraryService
from src.domain.services.certification.compliance_checklist_service import ComplianceChecklistService
from src.domain.services.certification.certification_evidence_assembly_service import CertificationEvidenceAssemblyService
from src.domain.services.supplier.supplier_registry_service import SupplierRegistryService, SupplierProfile
from src.domain.services.supplier.material_lot_tracker_service import MaterialLotTrackerService
from src.domain.services.supplier.ndt_integration_service import NDTIntegrationService
from src.domain.services.supplier.supplier_car_service import SupplierCARService
from src.domain.services.digital_factory.production_dashboard_service import ProductionDashboardService
from src.domain.services.digital_factory.shop_floor_data_collector_service import ShopFloorDataCollectorService
from src.domain.services.digital_factory.shop_floor_event_emitter_service import ShopFloorEventEmitterService
from src.domain.services.digital_factory.digital_twin_synchronizer_service import DigitalTwinSynchronizerService
from src.domain.services.generative_design.uncertainty_quantification_service import UncertaintyQuantificationService
from src.domain.services.generative_design.seven_discipline_mdo_service import SevenDisciplineMDOService
from src.domain.services.gdt.gdt_annotation_service import GDTAnnotationService
from src.domain.services.data_governance.dataset_versioning_service import DatasetVersioningService
from src.domain.services.data_governance.dataset_drift_detection_service import DatasetDriftDetectionService
from src.domain.services.data_governance.dataset_quality_score_service import DatasetQualityScoreService
from src.domain.services.fleet_intelligence.phm_model_confidence_service import PHMModelConfidenceService
from src.domain.services.fleet_intelligence.maintenance_decision_audit_service import MaintenanceDecisionAuditService
from src.domain.services.configuration_management.incremental_topology_propagation_service import IncrementalTopologyPropagationService
from src.domain.services.configuration_management.propagation_consistency_verifier_service import PropagationConsistencyVerifierService
from src.domain.services.integration.cross_program_event_orchestrator_service import CrossProgramEventOrchestratorService


@pytest.fixture
def config_mgr():
    return ConfigurationManagerService()


@pytest.fixture
def propagation_svc():
    return ThreeViewConfigPropagationService()


@pytest.fixture
def baseline_svc():
    return ConfigurationBaselineService()


@pytest.fixture
def change_ctrl_svc():
    return ConfigurationChangeControlService()


@pytest.fixture
def trace_svc():
    return RequirementsTraceabilityService()


@pytest.fixture
def regulatory_svc():
    return RegulatoryLibraryService()


@pytest.fixture
def checklist_svc():
    return ComplianceChecklistService()


@pytest.fixture
def evidence_svc():
    return CertificationEvidenceAssemblyService()


@pytest.fixture
def registry():
    return SupplierRegistryService()


@pytest.fixture
def lot_tracker():
    return MaterialLotTrackerService()


@pytest.fixture
def ndt_svc():
    return NDTIntegrationService()


@pytest.fixture
def car_svc():
    return SupplierCARService()


@pytest.fixture
def dashboard_svc():
    return ProductionDashboardService()


@pytest.fixture
def data_collector():
    return ShopFloorDataCollectorService()


@pytest.fixture
def emitter():
    return ShopFloorEventEmitterService()


@pytest.fixture
def twin_sync():
    return DigitalTwinSynchronizerService()


@pytest.fixture
def uq_svc():
    return UncertaintyQuantificationService()


@pytest.fixture
def mdo_svc():
    return SevenDisciplineMDOService()


@pytest.fixture
def gdt_svc():
    return GDTAnnotationService()


@pytest.fixture
def versioning_svc():
    return DatasetVersioningService()


@pytest.fixture
def drift_svc():
    return DatasetDriftDetectionService()


@pytest.fixture
def quality_svc():
    return DatasetQualityScoreService()


@pytest.fixture
def phm_svc():
    return PHMModelConfidenceService()


@pytest.fixture
def audit_svc():
    return MaintenanceDecisionAuditService()


@pytest.fixture
def topo_prop_svc():
    return IncrementalTopologyPropagationService()


@pytest.fixture
def consistency_svc():
    return PropagationConsistencyVerifierService()


@pytest.fixture
def orchestrator():
    return CrossProgramEventOrchestratorService()