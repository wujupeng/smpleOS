"""AeroForge-X V6.1 Integration Tests - GDT Digital Thread
IT-G04: createAnnotation → defineDatum → analyzeChain → linkOperation → assessDeviation → updateChain
REQ-VP-052
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "aircraft-core-service"))

import pytest

from src.domain.services.gdt.gdt_annotation_service import (
    GDTAnnotationService, ToleranceType, FormToleranceName,
    OrientationToleranceName, DatumType, ToleranceChainStep,
    ToleranceChainDefinition, AnalysisMethod,
)


@pytest.fixture
def service():
    return GDTAnnotationService()


class TestGDTDigitalThread:

    def test_full_gdt_digital_thread(self, service):
        ann1 = service.createGDTAnnotation("PART-001", ToleranceType.FORM,
                                            FormToleranceName.FLATNESS.value, 0.05)
        ann2 = service.createGDTAnnotation("PART-001", ToleranceType.ORIENTATION,
                                            OrientationToleranceName.PERPENDICULARITY.value, 0.02)
        ann3 = service.createGDTAnnotation("PART-001", ToleranceType.FORM,
                                            FormToleranceName.CIRCULARITY.value, 0.03)

        datum_a = service.defineDatum("PART-001", DatumType.PRIMARY, "Surface-A", "DRF-1")
        datum_b = service.defineDatum("PART-001", DatumType.SECONDARY, "Surface-B", "DRF-1")

        chain = ToleranceChainDefinition(
            chain_id="CHAIN-ASM-001",
            assembly_id="ASM-WING-001",
            steps=[
                ToleranceChainStep(step_id="S1", annotation_id=ann1.annotation_id, tolerance_value=0.05),
                ToleranceChainStep(step_id="S2", annotation_id=ann2.annotation_id, tolerance_value=0.02),
                ToleranceChainStep(step_id="S3", annotation_id=ann3.annotation_id, tolerance_value=0.03),
            ],
            analysis_method=AnalysisMethod.STATISTICAL_RSS,
            target_assembly_tolerance=0.08,
        )
        analysis = service.analyzeToleranceChain(chain)
        assert analysis.worst_case_result == 0.10
        assert analysis.statistical_result < analysis.worst_case_result

        for ann in [ann1, ann2, ann3]:
            service.linkGDTToDigitalThread(ann.annotation_id, f"OP-{ann.annotation_id}")

        deviation = service.assessMeasurementDeviation(ann1.annotation_id, 0.06)
        assert deviation.deviation == 0.01

        if not analysis.is_within_tolerance:
            suggestion = service.suggestToleranceReallocation(analysis)
            assert len(suggestion.suggested_allocation) > 0