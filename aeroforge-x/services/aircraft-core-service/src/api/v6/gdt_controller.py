from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.gdt.gdt_annotation_service import (
    GDTAnnotationService,
    ToleranceType,
    DatumType,
    ToleranceChainDefinition,
    ToleranceChainStep,
    AnalysisMethod,
)

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["GD&T v6"])

_gdt_service = GDTAnnotationService()


@router.post("/gdt-annotations")
async def create_gdt_annotation(body: dict[str, Any]):
    annotation = _gdt_service.createGDTAnnotation(
        part_id=body.get("part_id", ""),
        tolerance_type=ToleranceType(body.get("tolerance_type", "Form")),
        tolerance_name=body.get("tolerance_name", "Flatness"),
        tolerance_value=body.get("tolerance_value", 0.01),
        unit=body.get("unit", "mm"),
    )
    return annotation.to_dict()


@router.post("/gdt-datum-definitions")
async def define_datum(body: dict[str, Any]):
    datum = _gdt_service.defineDatum(
        part_id=body.get("part_id", ""),
        datum_type=DatumType(body.get("datum_type", "Primary")),
        datum_feature=body.get("datum_feature", ""),
        datum_reference_frame=body.get("datum_reference_frame", ""),
    )
    return datum.to_dict()


@router.post("/tolerance-chain-analysis")
async def analyze_tolerance_chain(body: dict[str, Any]):
    steps_data = body.get("steps", [])
    steps = [
        ToleranceChainStep(
            step_id=s.get("step_id", ""),
            annotation_id=s.get("annotation_id", ""),
            tolerance_value=s.get("tolerance_value", 0.0),
            nominal_dimension=s.get("nominal_dimension", 0.0),
        )
        for s in steps_data
    ]
    chain_def = ToleranceChainDefinition(
        chain_id=body.get("chain_id", ""),
        assembly_id=body.get("assembly_id", ""),
        steps=steps,
        analysis_method=AnalysisMethod(body.get("analysis_method", "Statistical_RSS")),
        target_assembly_tolerance=body.get("target_assembly_tolerance", 0.1),
    )
    analysis = _gdt_service.analyzeToleranceChain(chain_def=chain_def)
    return analysis.to_dict()


@router.post("/tolerance-chain-reallocation")
async def suggest_tolerance_reallocation(body: dict[str, Any]):
    from src.domain.services.gdt.gdt_annotation_service import ToleranceChainAnalysis
    analysis = ToleranceChainAnalysis(
        chain_id=body.get("chain_id", ""),
        worst_case_result=body.get("worst_case_result", 0.0),
        statistical_result=body.get("statistical_result", 0.0),
        is_within_tolerance=body.get("is_within_tolerance", False),
    )
    suggestion = _gdt_service.suggestToleranceReallocation(analysis=analysis)
    return suggestion.to_dict()


@router.post("/gdt-annotations/{annotation_id}/link-digital-thread")
async def link_gdt_to_digital_thread(annotation_id: str, body: dict[str, Any]):
    operation_id = body.get("operation_id", "")
    try:
        annotation = _gdt_service.linkGDTToDigitalThread(
            annotation_id=annotation_id, operation_id=operation_id
        )
        return annotation.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/gdt-annotations/{annotation_id}/assess-deviation")
async def assess_measurement_deviation(annotation_id: str, body: dict[str, Any]):
    actual = body.get("actual", 0.0)
    try:
        assessment = _gdt_service.assessMeasurementDeviation(
            annotation_id=annotation_id, actual=actual
        )
        return assessment.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))