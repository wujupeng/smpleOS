from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.supplier.supplier_registry_service import (
    SupplierRegistryService,
    SupplierProfile,
    ChangeClass,
)
from src.domain.services.supplier.material_lot_tracker_service import (
    MaterialLotTrackerService,
    MaterialLot,
    LotStatus,
)
from src.domain.services.supplier.ndt_integration_service import (
    NDTIntegrationService,
    NDTRecord,
    NDTMethod,
    NDTResult,
    NDTFilter,
)

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Supplier Digital Thread v6"])

_supplier_service = SupplierRegistryService()
_lot_service = MaterialLotTrackerService()
_ndt_service = NDTIntegrationService()


@router.post("/suppliers")
async def register_supplier(body: dict[str, Any]):
    profile = SupplierProfile(
        supplier_id=body.get("supplier_id", ""),
        company_name=body.get("company_name", ""),
        certifications=body.get("certifications", []),
        capability_matrix=body.get("capability_matrix", {}),
    )
    try:
        result = _supplier_service.registerSupplier(profile=profile)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/suppliers/{supplier_id}/approval-workflow")
async def approve_supplier_workflow(supplier_id: str):
    try:
        workflow = _supplier_service.approveSupplierWorkflow(supplier_id=supplier_id)
        return workflow.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/suppliers/{supplier_id}/quality-rating")
async def compute_supplier_quality_rating(supplier_id: str, body: dict[str, Any]):
    try:
        _supplier_service.updateRatingMetrics(
            supplier_id=supplier_id,
            on_time_delivery_rate=body.get("on_time_delivery_rate"),
            first_pass_yield=body.get("first_pass_yield"),
            defect_rate=body.get("defect_rate"),
            car_responsiveness=body.get("car_responsiveness"),
            audit_findings_score=body.get("audit_findings_score"),
        )
        rating = _supplier_service.computeQualityRating(supplier_id=supplier_id)
        return rating.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/suppliers/{supplier_id}/suspend")
async def suspend_supplier(supplier_id: str, body: dict[str, Any]):
    reason = body.get("reason", "")
    try:
        result = _supplier_service.suspendSupplier(supplier_id=supplier_id, reason=reason)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/suppliers/{supplier_id}/supply-chain-impact")
async def assess_supply_chain_impact(supplier_id: str):
    try:
        report = _supplier_service.assessSupplyChainImpact(supplier_id=supplier_id)
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/material-lots")
async def receive_material_lot(body: dict[str, Any]):
    lot = MaterialLot(
        lot_id=body.get("lot_id", ""),
        supplier_id=body.get("supplier_id", ""),
        material_specification=body.get("material_specification", ""),
        heat_number=body.get("heat_number", ""),
        certificate_of_conformance=body.get("certificate_of_conformance", ""),
    )
    try:
        result = _lot_service.receiveMaterialLot(lot_data=lot)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/material-lots/{lot_id}/forward-trace")
async def forward_traceability(lot_id: str):
    try:
        result = _lot_service.forwardTraceability(lot_id=lot_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/material-lots/backward-trace")
async def backward_traceability(body: dict[str, Any]):
    part_serial_id = body.get("part_serial_id", "")
    result = _lot_service.backwardTraceability(part_serial_id=part_serial_id)
    return result.to_dict()


@router.post("/material-lots/{lot_id}/flag-non-conforming")
async def flag_non_conforming_lot(lot_id: str):
    try:
        result = _lot_service.flagNonConformingLot(lot_id=lot_id)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/material-genealogy")
async def record_genealogy_step(body: dict[str, Any]):
    from src.domain.services.supplier.material_lot_tracker_service import GenealogyStep, TransformationType
    step = GenealogyStep(
        step_id="",
        lot_id=body.get("lot_id", ""),
        transformation_type=TransformationType(body.get("transformation_type", "RawToSemiFinished")),
        process_parameters=body.get("process_parameters", {}),
        output_lot_id=body.get("output_lot_id", ""),
    )
    try:
        result = _lot_service.recordGenealogyStep(step=step)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ndt-records")
async def import_ndt_record(body: dict[str, Any]):
    record = NDTRecord(
        ndt_id=body.get("ndt_id", ""),
        part_id=body.get("part_id", ""),
        inspection_method=NDTMethod(body.get("inspection_method", "UT")),
        result=NDTResult(body.get("result", "Accept")),
        linked_lot_id=body.get("linked_lot_id", ""),
    )
    try:
        result = _ndt_service.importNDTRecord(ndt_data=record)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ndt-statistics")
async def compute_ndt_statistics(body: dict[str, Any]):
    ndt_filter = None
    if body.get("filter"):
        f = body["filter"]
        ndt_filter = NDTFilter(
            supplier_id=f.get("supplier_id", ""),
            method=NDTMethod(f["method"]) if f.get("method") else None,
            part_id=f.get("part_id", ""),
        )
    stats = _ndt_service.computeNDTStatistics(ndt_filter=ndt_filter)
    return stats.to_dict()