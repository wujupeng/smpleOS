from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.aerodynamic_database_service import AerodynamicDatabaseService

router = APIRouter(prefix="/api/v4/physics-twin/aero-databases", tags=["Aerodynamic Database v4"])

_service = AerodynamicDatabaseService()


@router.post("")
async def create_aero_database(body: dict[str, Any]):
    result = _service.load_database(
        database_id=body.get("database_id", ""),
        database_name=body.get("database_name", ""),
        alpha_range=tuple(body.get("alpha_range", [-10.0, 25.0])),
        alpha_resolution=body.get("alpha_resolution", 1.0),
        beta_range=tuple(body.get("beta_range", [-15.0, 15.0])),
        beta_resolution=body.get("beta_resolution", 1.0),
        mach_range=tuple(body.get("mach_range", [0.1, 0.8])),
        mach_resolution=body.get("mach_resolution", 0.1),
        reynolds_range=tuple(body.get("reynolds_range", [1e6, 5e7])),
        reynolds_resolution=body.get("reynolds_resolution", 1e7),
        coefficient_types=body.get("coefficient_types"),
        data_source=body.get("data_source", "internal"),
        quality_status=body.get("quality_status", "draft"),
        applicable_config=body.get("applicable_config", ""),
        partial_coverage_dimensions=body.get("partial_coverage_dimensions"),
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "database_id": result.database_id,
        "message": result.message,
        "coefficient_count": result.coefficient_count,
        "is_partial_coverage": result.is_partial_coverage,
    }


@router.get("")
async def list_aero_databases():
    return _service.list_databases()


@router.get("/{database_id}")
async def get_aero_database(database_id: str):
    meta = _service.get_database_metadata(database_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Database '{database_id}' not found")
    return meta


@router.put("/{database_id}/activate")
async def activate_aero_database(database_id: str):
    result = _service.switch_database(database_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)
    return {
        "previous_database_id": result.previous_database_id,
        "new_database_id": result.new_database_id,
        "message": result.message,
    }


@router.post("/{database_id}/hot-reload")
async def hot_reload_aero_database(database_id: str, body: dict[str, Any]):
    from src.domain.plugins.aerodynamic_database import FourDimLookupTable

    table_data = body.get("table")
    if not table_data:
        raise HTTPException(status_code=400, detail="Table data required for hot-reload")

    new_table = FourDimLookupTable(
        database_id=database_id,
        database_name=table_data.get("database_name", ""),
        alpha_range=tuple(table_data.get("alpha_range", [-10.0, 25.0])),
        alpha_resolution=table_data.get("alpha_resolution", 1.0),
        beta_range=tuple(table_data.get("beta_range", [-15.0, 15.0])),
        beta_resolution=table_data.get("beta_resolution", 1.0),
        mach_range=tuple(table_data.get("mach_range", [0.1, 0.8])),
        mach_resolution=table_data.get("mach_resolution", 0.1),
        reynolds_range=tuple(table_data.get("reynolds_range", [1e6, 5e7])),
        reynolds_resolution=table_data.get("reynolds_resolution", 1e7),
        coefficient_types=table_data.get("coefficient_types"),
        data_source=table_data.get("data_source", "internal"),
        quality_status=table_data.get("quality_status", "draft"),
        applicable_config=table_data.get("applicable_config", ""),
        partial_coverage_dimensions=table_data.get("partial_coverage_dimensions"),
    )

    result = _service.hot_reload_database(database_id, new_table)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "database_id": result.database_id,
        "message": result.message,
        "old_version_active": result.old_version_active,
    }


@router.post("/query")
async def query_aero_coefficients(body: dict[str, Any]):
    alpha = body.get("alpha", 0.0)
    beta = body.get("beta", 0.0)
    mach = body.get("mach", 0.0)
    reynolds = body.get("reynolds", 1e7)

    coeffs = _service.query_coefficients(alpha, beta, mach, reynolds)
    return {
        "CL": coeffs.CL,
        "CD": coeffs.CD,
        "CM": coeffs.CM,
        "CY": coeffs.CY,
        "Cl": coeffs.Cl,
        "Cn": coeffs.Cn,
        "is_extrapolated": coeffs.is_extrapolated,
        "extrapolation_warning": coeffs.extrapolation_warning,
        "nearest_boundary_alpha": coeffs.nearest_boundary_alpha,
        "nearest_boundary_beta": coeffs.nearest_boundary_beta,
    }


@router.post("/{database_id}/validate")
async def validate_aero_database(database_id: str):
    result = _service.validate_data_integrity(database_id)
    return {
        "is_valid": result.is_valid,
        "database_id": result.database_id,
        "nan_count": result.nan_count,
        "inf_count": result.inf_count,
        "negative_drag_count": result.negative_drag_count,
        "warnings": result.warnings,
    }


@router.post("/import/openvsp")
async def import_openvsp(body: dict[str, Any]):
    file_path = body.get("file_path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path required")
    result = _service.import_external_data("OpenVSP", file_path, body.get("config"))
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "database_id": result.database_id,
        "message": result.message,
        "coefficient_count": result.coefficient_count,
        "is_partial_coverage": result.is_partial_coverage,
    }


@router.post("/import/avl")
async def import_avl(body: dict[str, Any]):
    file_path = body.get("file_path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path required")
    result = _service.import_external_data("AVL", file_path, body.get("config"))
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "database_id": result.database_id,
        "message": result.message,
        "coefficient_count": result.coefficient_count,
        "is_partial_coverage": result.is_partial_coverage,
    }


@router.post("/import/openfoam")
async def import_openfoam(body: dict[str, Any]):
    file_path = body.get("file_path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path required")
    result = _service.import_external_data("OpenFOAM", file_path, body.get("config"))
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "database_id": result.database_id,
        "message": result.message,
        "coefficient_count": result.coefficient_count,
        "is_partial_coverage": result.is_partial_coverage,
    }


@router.post("/merge")
async def merge_aero_databases(body: dict[str, Any]):
    source_ids = body.get("source_ids", [])
    priority = body.get("priority", "high_fidelity")
    if len(source_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 source database IDs required")
    result = _service.merge_databases(source_ids, priority)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "database_id": result.database_id,
        "message": result.message,
        "coefficient_count": result.coefficient_count,
        "is_partial_coverage": result.is_partial_coverage,
    }