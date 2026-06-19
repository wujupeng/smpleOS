"""AeroForge-X V6.1 Performance Tests - API Response Performance
V61-PERF2.3: All v6.0 RESTful endpoints P95 <500ms (simulated)
REQ-VP-061, REQ-VP-062
"""

import sys
import os
import time
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "physics-twin-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "workflow-engine-service"))

import pytest

from src.domain.services.configuration_management.configuration_manager_service import ConfigurationManagerService
from src.domain.services.certification.regulatory_library_service import RegulatoryLibraryService, RegulationType
from src.domain.services.certification.compliance_checklist_service import ComplianceChecklistService
from src.domain.services.supplier.supplier_registry_service import SupplierRegistryService, SupplierProfile
from src.domain.services.digital_factory.production_dashboard_service import ProductionDashboardService
from src.domain.services.generative_design.uncertainty_quantification_service import (
    UncertaintyQuantificationService, UQMethodType, UQMethodSpec,
)
from src.domain.services.data_governance.dataset_versioning_service import DatasetVersioningService
from src.domain.services.fleet_intelligence.phm_model_confidence_service import PHMModelConfidenceService


def measure_p95(func, iterations=50):
    latencies = []
    for _ in range(iterations):
        start = time.monotonic()
        func()
        elapsed = (time.monotonic() - start) * 1000.0
        latencies.append(elapsed)
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    return latencies[p95_idx]


class TestAPIResponsePerformance:

    def test_config_api_p95_under_500ms(self):
        svc = ConfigurationManagerService()
        p95 = measure_p95(lambda: svc.createBlockConfig("A320", "Block-1"))
        assert p95 < 500, f"createBlockConfig P95={p95:.1f}ms > 500ms"

    def test_regulation_api_p95_under_500ms(self):
        svc = RegulatoryLibraryService()
        p95 = measure_p95(lambda: svc.importRegulation(RegulationType.FAA_PART_25, "FAA Part 25", "v1"))
        assert p95 < 500, f"importRegulation P95={p95:.1f}ms > 500ms"

    def test_checklist_api_p95_under_500ms(self):
        reg_svc = RegulatoryLibraryService()
        lib = reg_svc.importRegulation(RegulationType.FAA_PART_23, "FAA Part 23", "v1")
        check_svc = ComplianceChecklistService()
        p95 = measure_p95(lambda: check_svc.generateChecklist(lib, "PROJ-001"))
        assert p95 < 500, f"generateChecklist P95={p95:.1f}ms > 500ms"

    def test_supplier_api_p95_under_500ms(self):
        svc = SupplierRegistryService()
        counter = [0]

        def create_supplier():
            counter[0] += 1
            svc.registerSupplier(SupplierProfile(
                supplier_id=f"SUP-{counter[0]}",
                company_name=f"Company-{counter[0]}",
            ))

        p95 = measure_p95(create_supplier)
        assert p95 < 500, f"registerSupplier P95={p95:.1f}ms > 500ms"

    def test_oee_api_p95_under_500ms(self):
        svc = ProductionDashboardService()

        def compute():
            svc.computeOEE("EQ-001", 480, 432, 1.0, 1.1, 390, 370)

        p95 = measure_p95(compute)
        assert p95 < 500, f"computeOEE P95={p95:.1f}ms > 500ms"

    def test_uq_predict_api_p95_under_500ms(self):
        svc = UncertaintyQuantificationService()
        svc.registerUQMethod(UQMethodSpec(
            method_id="UQ-EN", method_type=UQMethodType.ENSEMBLE,
            hyperparameters={"num_models": 5, "seeds": [1, 2, 3, 4, 5]},
        ))
        p95 = measure_p95(lambda: svc.predictWithUQ({"CL": 0.5}, method="UQ-EN"))
        assert p95 < 500, f"predictWithUQ P95={p95:.1f}ms > 500ms"

    def test_dataset_version_api_p95_under_500ms(self):
        svc = DatasetVersioningService()
        counter = [0]

        def create():
            counter[0] += 1
            svc.createDatasetVersion(f"DS-{counter[0]}", 1, 0, 0)

        p95 = measure_p95(create)
        assert p95 < 500, f"createDatasetVersion P95={p95:.1f}ms > 500ms"

    def test_phm_predict_api_p95_under_500ms(self):
        svc = PHMModelConfidenceService()
        p95 = measure_p95(lambda: svc.predictWithConfidence("ENG-001", 5000.0, [4800, 4900, 5000, 5100, 5200]))
        assert p95 < 500, f"predictWithConfidence P95={p95:.1f}ms > 500ms"