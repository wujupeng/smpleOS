"""AeroForge-X v6.0 GDTAnnotationService

Manages GD&T (Geometric Dimensioning and Tolerancing) annotations,
datum definitions, tolerance chain analysis, and digital thread integration.
REQ-E-ENH-015~020
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ToleranceType(str, Enum):
    FORM = "Form"
    ORIENTATION = "Orientation"
    LOCATION = "Location"


class FormToleranceName(str, Enum):
    FLATNESS = "Flatness"
    CIRCULARITY = "Circularity"
    CYLINDRICITY = "Cylindricity"


class OrientationToleranceName(str, Enum):
    PARALLELISM = "Parallelism"
    PERPENDICULARITY = "Perpendicularity"
    ANGULARITY = "Angularity"


class LocationToleranceName(str, Enum):
    POSITION = "Position"
    CONCENTRICITY = "Concentricity"


class DatumType(str, Enum):
    PRIMARY = "Primary"
    SECONDARY = "Secondary"
    TERTIARY = "Tertiary"


class AnalysisMethod(str, Enum):
    WORST_CASE = "WorstCase"
    STATISTICAL_RSS = "Statistical_RSS"


@dataclass
class GDTAnnotation:
    annotation_id: str
    part_id: str
    tolerance_type: ToleranceType
    tolerance_name: str
    tolerance_value: float
    unit: str = "mm"
    datum_references: list[str] = field(default_factory=list)
    linked_operation_id: str = ""

    def to_dict(self) -> dict:
        return {
            "annotation_id": self.annotation_id,
            "part_id": self.part_id,
            "tolerance_type": self.tolerance_type.value,
            "tolerance_name": self.tolerance_name,
            "tolerance_value": self.tolerance_value,
            "unit": self.unit,
            "datum_references": self.datum_references,
            "linked_operation_id": self.linked_operation_id,
        }


@dataclass
class DatumDefinition:
    datum_type: DatumType
    datum_feature: str
    datum_reference_frame: str = ""

    def to_dict(self) -> dict:
        return {
            "datum_type": self.datum_type.value,
            "datum_feature": self.datum_feature,
            "datum_reference_frame": self.datum_reference_frame,
        }


@dataclass
class ToleranceChainStep:
    step_id: str
    annotation_id: str
    tolerance_value: float
    nominal_dimension: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "annotation_id": self.annotation_id,
            "tolerance_value": self.tolerance_value,
            "nominal_dimension": self.nominal_dimension,
        }


@dataclass
class ToleranceChainDefinition:
    chain_id: str
    assembly_id: str
    steps: list[ToleranceChainStep] = field(default_factory=list)
    analysis_method: AnalysisMethod = AnalysisMethod.STATISTICAL_RSS
    target_assembly_tolerance: float = 0.0


@dataclass
class ToleranceChainAnalysis:
    chain_id: str
    worst_case_result: float = 0.0
    statistical_result: float = 0.0
    is_within_tolerance: bool = False
    contributing_tolerances: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chain_id": self.chain_id,
            "worst_case_result": self.worst_case_result,
            "statistical_result": self.statistical_result,
            "is_within_tolerance": self.is_within_tolerance,
            "contributing_tolerances": self.contributing_tolerances,
        }


@dataclass
class ReallocationSuggestion:
    chain_id: str
    current_allocation: list[dict] = field(default_factory=list)
    suggested_allocation: list[dict] = field(default_factory=list)
    expected_result: float = 0.0

    def to_dict(self) -> dict:
        return {
            "chain_id": self.chain_id,
            "current_allocation": self.current_allocation,
            "suggested_allocation": self.suggested_allocation,
            "expected_result": self.expected_result,
        }


@dataclass
class DeviationAssessment:
    annotation_id: str
    actual_value: float
    deviation: float
    impact_on_downstream_assembly: str = ""

    def to_dict(self) -> dict:
        return {
            "annotation_id": self.annotation_id,
            "actual_value": self.actual_value,
            "deviation": self.deviation,
            "impact_on_downstream_assembly": self.impact_on_downstream_assembly,
        }


class GDTAnnotationService:

    def __init__(self) -> None:
        self._annotations: dict[str, GDTAnnotation] = {}
        self._datums: dict[str, list[DatumDefinition]] = {}
        self._chains: dict[str, ToleranceChainDefinition] = {}
        self._analyses: dict[str, ToleranceChainAnalysis] = {}

    def createGDTAnnotation(
        self, part_id: str, tolerance_type: ToleranceType,
        tolerance_name: str, tolerance_value: float, unit: str = "mm"
    ) -> GDTAnnotation:
        annotation_id = f"GDT-{part_id}-{uuid.uuid4().hex[:6]}"

        annotation = GDTAnnotation(
            annotation_id=annotation_id,
            part_id=part_id,
            tolerance_type=tolerance_type,
            tolerance_name=tolerance_name,
            tolerance_value=tolerance_value,
            unit=unit,
        )
        self._annotations[annotation_id] = annotation
        return annotation

    def defineDatum(
        self, part_id: str, datum_type: DatumType,
        datum_feature: str, datum_reference_frame: str = ""
    ) -> DatumDefinition:
        datum = DatumDefinition(
            datum_type=datum_type,
            datum_feature=datum_feature,
            datum_reference_frame=datum_reference_frame,
        )
        if part_id not in self._datums:
            self._datums[part_id] = []
        self._datums[part_id].append(datum)
        return datum

    def analyzeToleranceChain(
        self, chain_def: ToleranceChainDefinition
    ) -> ToleranceChainAnalysis:
        if not chain_def.steps:
            return ToleranceChainAnalysis(chain_id=chain_def.chain_id)

        tolerances = [s.tolerance_value for s in chain_def.steps]

        worst_case = sum(tolerances)

        import math
        statistical = math.sqrt(sum(t ** 2 for t in tolerances))

        is_within = statistical <= chain_def.target_assembly_tolerance

        contributing = sorted(
            [
                {"step_id": s.step_id, "tolerance_value": s.tolerance_value,
                 "contribution_pct": round(s.tolerance_value ** 2 / sum(t ** 2 for t in tolerances) * 100, 2)}
                for s in chain_def.steps
            ],
            key=lambda x: x["contribution_pct"],
            reverse=True,
        )

        analysis = ToleranceChainAnalysis(
            chain_id=chain_def.chain_id,
            worst_case_result=round(worst_case, 4),
            statistical_result=round(statistical, 4),
            is_within_tolerance=is_within,
            contributing_tolerances=contributing,
        )
        self._analyses[chain_def.chain_id] = analysis
        self._chains[chain_def.chain_id] = chain_def
        return analysis

    def suggestToleranceReallocation(
        self, analysis: ToleranceChainAnalysis
    ) -> ReallocationSuggestion:
        if analysis.is_within_tolerance:
            return ReallocationSuggestion(chain_id=analysis.chain_id)

        chain = self._chains.get(analysis.chain_id)
        if not chain:
            return ReallocationSuggestion(chain_id=analysis.chain_id)

        current = [
            {"step_id": s.step_id, "tolerance_value": s.tolerance_value}
            for s in chain.steps
        ]

        n = len(chain.steps)
        if n == 0:
            return ReallocationSuggestion(chain_id=analysis.chain_id)

        equal_tolerance = chain.target_assembly_tolerance / math.sqrt(n) if n > 0 else 0
        suggested = [
            {"step_id": s.step_id, "suggested_tolerance": round(equal_tolerance, 4)}
            for s in chain.steps
        ]

        import math
        expected = math.sqrt(n * equal_tolerance ** 2) if n > 0 else 0

        return ReallocationSuggestion(
            chain_id=analysis.chain_id,
            current_allocation=current,
            suggested_allocation=suggested,
            expected_result=round(expected, 4),
        )

    def linkGDTToDigitalThread(
        self, annotation_id: str, operation_id: str
    ) -> GDTAnnotation:
        if annotation_id not in self._annotations:
            raise ValueError(f"Annotation not found: {annotation_id}")

        annotation = self._annotations[annotation_id]
        annotation.linked_operation_id = operation_id
        return annotation

    def assessMeasurementDeviation(
        self, annotation_id: str, actual: float
    ) -> DeviationAssessment:
        if annotation_id not in self._annotations:
            raise ValueError(f"Annotation not found: {annotation_id}")

        annotation = self._annotations[annotation_id]
        deviation = actual - annotation.tolerance_value

        impact = ""
        if abs(deviation) > annotation.tolerance_value * 0.5:
            impact = "Significant impact on downstream assembly"
        elif abs(deviation) > annotation.tolerance_value * 0.2:
            impact = "Minor impact, monitor closely"
        else:
            impact = "Within acceptable range"

        return DeviationAssessment(
            annotation_id=annotation_id,
            actual_value=actual,
            deviation=round(deviation, 4),
            impact_on_downstream_assembly=impact,
        )

    def getAnnotation(self, annotation_id: str) -> Optional[GDTAnnotation]:
        return self._annotations.get(annotation_id)