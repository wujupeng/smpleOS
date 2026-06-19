"""AeroForge-X V6.0/V6.1 Unit Tests - GDTAnnotationService
REQ-E-ENH-015~020, REQ-VP-020
"""

import pytest

from src.domain.services.gdt.gdt_annotation_service import (
    GDTAnnotationService,
    ToleranceType,
    FormToleranceName,
    OrientationToleranceName,
    LocationToleranceName,
    DatumType,
    AnalysisMethod,
    GDTAnnotation,
    DatumDefinition,
    ToleranceChainStep,
    ToleranceChainDefinition,
    ToleranceChainAnalysis,
    DeviationAssessment,
)


@pytest.fixture
def service():
    return GDTAnnotationService()


class TestCreateGDTAnnotation:

    def test_create_annotation(self, service):
        ann = service.createGDTAnnotation(
            part_id="PART-001",
            tolerance_type=ToleranceType.FORM,
            tolerance_name=FormToleranceName.FLATNESS.value,
            tolerance_value=0.05,
        )
        assert isinstance(ann, GDTAnnotation)
        assert ann.annotation_id.startswith("GDT-")
        assert ann.part_id == "PART-001"
        assert ann.tolerance_value == 0.05

    def test_create_orientation_annotation(self, service):
        ann = service.createGDTAnnotation(
            part_id="PART-001",
            tolerance_type=ToleranceType.ORIENTATION,
            tolerance_name=OrientationToleranceName.PERPENDICULARITY.value,
            tolerance_value=0.02,
        )
        assert ann.tolerance_type == ToleranceType.ORIENTATION

    def test_create_location_annotation(self, service):
        ann = service.createGDTAnnotation(
            part_id="PART-001",
            tolerance_type=ToleranceType.LOCATION,
            tolerance_name=LocationToleranceName.POSITION.value,
            tolerance_value=0.1,
        )
        assert ann.tolerance_type == ToleranceType.LOCATION


class TestDefineDatum:

    def test_define_primary_datum(self, service):
        datum = service.defineDatum("PART-001", DatumType.PRIMARY, "Surface-A")
        assert isinstance(datum, DatumDefinition)
        assert datum.datum_type == DatumType.PRIMARY
        assert datum.datum_feature == "Surface-A"

    def test_define_multiple_datums(self, service):
        service.defineDatum("PART-001", DatumType.PRIMARY, "Surface-A")
        service.defineDatum("PART-001", DatumType.SECONDARY, "Surface-B")
        service.defineDatum("PART-001", DatumType.TERTIARY, "Surface-C")
        assert len(service._datums["PART-001"]) == 3


class TestAnalyzeToleranceChain:

    def test_analyze_chain_within_tolerance(self, service):
        chain = ToleranceChainDefinition(
            chain_id="CHAIN-001",
            assembly_id="ASM-001",
            steps=[
                ToleranceChainStep(step_id="S1", annotation_id="A1", tolerance_value=0.02),
                ToleranceChainStep(step_id="S2", annotation_id="A2", tolerance_value=0.03),
            ],
            target_assembly_tolerance=0.1,
        )
        result = service.analyzeToleranceChain(chain)
        assert isinstance(result, ToleranceChainAnalysis)
        assert result.worst_case_result == 0.05
        assert result.statistical_result > 0
        assert result.is_within_tolerance is True

    def test_analyze_chain_exceeds_tolerance(self, service):
        chain = ToleranceChainDefinition(
            chain_id="CHAIN-002",
            assembly_id="ASM-001",
            steps=[
                ToleranceChainStep(step_id="S1", annotation_id="A1", tolerance_value=0.1),
                ToleranceChainStep(step_id="S2", annotation_id="A2", tolerance_value=0.1),
            ],
            target_assembly_tolerance=0.05,
        )
        result = service.analyzeToleranceChain(chain)
        assert result.is_within_tolerance is False

    def test_analyze_empty_chain(self, service):
        chain = ToleranceChainDefinition(
            chain_id="CHAIN-003",
            assembly_id="ASM-001",
            steps=[],
        )
        result = service.analyzeToleranceChain(chain)
        assert result.worst_case_result == 0

    def test_contributing_tolerances_sorted(self, service):
        chain = ToleranceChainDefinition(
            chain_id="CHAIN-004",
            assembly_id="ASM-001",
            steps=[
                ToleranceChainStep(step_id="S1", annotation_id="A1", tolerance_value=0.01),
                ToleranceChainStep(step_id="S2", annotation_id="A2", tolerance_value=0.05),
            ],
            target_assembly_tolerance=0.1,
        )
        result = service.analyzeToleranceChain(chain)
        assert result.contributing_tolerances[0]["contribution_pct"] >= result.contributing_tolerances[1]["contribution_pct"]


class TestSuggestToleranceReallocation:

    def test_suggest_reallocation(self, service):
        chain = ToleranceChainDefinition(
            chain_id="CHAIN-001",
            assembly_id="ASM-001",
            steps=[
                ToleranceChainStep(step_id="S1", annotation_id="A1", tolerance_value=0.1),
                ToleranceChainStep(step_id="S2", annotation_id="A2", tolerance_value=0.1),
            ],
            target_assembly_tolerance=0.05,
        )
        analysis = service.analyzeToleranceChain(chain)
        suggestion = service.suggestToleranceReallocation(analysis)
        assert len(suggestion.suggested_allocation) > 0

    def test_no_reallocation_needed(self, service):
        chain = ToleranceChainDefinition(
            chain_id="CHAIN-002",
            assembly_id="ASM-001",
            steps=[
                ToleranceChainStep(step_id="S1", annotation_id="A1", tolerance_value=0.02),
            ],
            target_assembly_tolerance=0.1,
        )
        analysis = service.analyzeToleranceChain(chain)
        suggestion = service.suggestToleranceReallocation(analysis)
        assert len(suggestion.suggested_allocation) == 0


class TestLinkGDTToDigitalThread:

    def test_link_annotation(self, service):
        ann = service.createGDTAnnotation("PART-001", ToleranceType.FORM, "Flatness", 0.05)
        result = service.linkGDTToDigitalThread(ann.annotation_id, "OP-001")
        assert result.linked_operation_id == "OP-001"

    def test_link_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.linkGDTToDigitalThread("FAKE-ID", "OP-001")


class TestAssessMeasurementDeviation:

    def test_assess_minor_deviation(self, service):
        ann = service.createGDTAnnotation("PART-001", ToleranceType.FORM, "Flatness", 0.05)
        result = service.assessMeasurementDeviation(ann.annotation_id, 0.055)
        assert isinstance(result, DeviationAssessment)
        assert result.deviation == 0.005

    def test_assess_significant_deviation(self, service):
        ann = service.createGDTAnnotation("PART-001", ToleranceType.FORM, "Flatness", 0.05)
        result = service.assessMeasurementDeviation(ann.annotation_id, 0.08)
        assert "Significant" in result.impact_on_downstream_assembly

    def test_assess_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.assessMeasurementDeviation("FAKE-ID", 0.1)