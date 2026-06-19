from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.domain.services.manufacturing.manufacturing_simulator_service import (
    ManufacturingSimulatorService,
    MachiningSimParams,
    AssemblySimParams,
    InspectionSimParams,
)

router = APIRouter(prefix="/api/v5/aircraft-core/manufacturing-sim", tags=["Manufacturing Simulation v5"])

_service = ManufacturingSimulatorService()


@router.post("/machining")
async def simulate_machining(body: dict[str, Any]):
    params = MachiningSimParams(
        material_properties=body.get("material_properties", {}),
        cutting_parameters=body.get("cutting_parameters", {}),
        fixture_configuration=body.get("fixture_configuration", {}),
    )
    tolerance = body.get("tolerance_mm", 0.1)
    result = _service.simulate_machining_deformation(params=params, tolerance_mm=tolerance)
    return {
        "max_deformation_mm": result.max_deformation_mm,
        "thermal_deformation_mm": result.thermal_deformation_mm,
        "residual_stress_deformation_mm": result.residual_stress_deformation_mm,
        "cutting_force_deformation_mm": result.cutting_force_deformation_mm,
        "clamping_deformation_mm": result.clamping_deformation_mm,
        "is_within_tolerance": result.is_within_tolerance,
    }


@router.post("/assembly")
async def simulate_assembly(body: dict[str, Any]):
    params = AssemblySimParams(
        part_tolerances=body.get("part_tolerances", []),
        assembly_sequence=body.get("assembly_sequence", []),
        joining_methods=body.get("joining_methods", []),
    )
    required_tol = body.get("required_tolerance_mm", 0.5)
    result = _service.simulate_assembly_accuracy(params=params, required_tolerance_mm=required_tol)
    return {
        "assembly_tolerance_mm": result.assembly_tolerance_mm,
        "required_tolerance_mm": result.required_tolerance_mm,
        "assembly_success_probability": result.assembly_success_probability,
        "is_within_tolerance": result.is_within_tolerance,
    }


@router.post("/inspection")
async def simulate_inspection(body: dict[str, Any]):
    params = InspectionSimParams(
        part_geometry=body.get("part_geometry", {}),
        tolerance_requirements=body.get("tolerance_requirements", []),
        measurement_system_capability=body.get("measurement_system_capability", 0.1),
    )
    min_cov = body.get("min_coverage", 0.95)
    result = _service.simulate_inspection_coverage(params=params, min_coverage=min_cov)
    return {
        "coverage_ratio": result.coverage_ratio,
        "total_features": result.total_features,
        "detected_features": result.detected_features,
        "measurement_uncertainty_mm": result.measurement_uncertainty_mm,
        "is_adequate": result.is_adequate,
    }


@router.post("/corrective-actions")
async def suggest_corrective_actions(body: dict[str, Any]):
    machining_result = None
    assembly_result = None
    inspection_result = None

    if "machining" in body:
        m = body["machining"]
        from src.domain.services.manufacturing.manufacturing_simulator_service import (
            MachiningDeformationResult,
        )
        machining_result = MachiningDeformationResult(
            max_deformation_mm=m.get("max_deformation_mm", 0),
            thermal_deformation_mm=m.get("thermal_deformation_mm", 0),
            residual_stress_deformation_mm=m.get("residual_stress_deformation_mm", 0),
            cutting_force_deformation_mm=m.get("cutting_force_deformation_mm", 0),
            clamping_deformation_mm=m.get("clamping_deformation_mm", 0),
            is_within_tolerance=m.get("is_within_tolerance", True),
        )

    actions = _service.suggest_corrective_actions(
        machining_result=machining_result,
        assembly_result=assembly_result,
        inspection_result=inspection_result,
    )
    return {
        "corrective_actions": [
            {
                "action_type": a.action_type,
                "description": a.description,
                "estimated_improvement": a.estimated_improvement,
                "priority": a.priority,
            }
            for a in actions
        ],
    }