from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..domain.entities.data_lake_job import DataFormat, DataSource
from ..domain.services.data_lake_service import AITrainingPlatformService, DataLakeService

router = APIRouter(prefix="/api/v1/datalake", tags=["data-lake"])
_lake_service = DataLakeService()
_ai_service = AITrainingPlatformService()


class IngestRequest(BaseModel):
    tenant_id: str
    data_source: str = "mes"
    data_format: str = "parquet"
    query: str = ""


class TransformRequest(BaseModel):
    tenant_id: str
    source_job_id: str
    transformation: str = "normalize"


class ExportRequest(BaseModel):
    tenant_id: str
    source_job_id: str
    export_format: str = "csv"


class AnalyzeRequest(BaseModel):
    tenant_id: str
    data_source: str = "mes"
    analysis_type: str = "correlation"


class CreateDatasetRequest(BaseModel):
    tenant_id: str
    name: str
    dataset_type: str = "quality_prediction"
    data_sources: list[str] | None = None


class StartTrainingRequest(BaseModel):
    tenant_id: str
    dataset_id: str
    model_type: str = "xgboost"
    objective: str = "quality_prediction"
    hyperparameters: dict[str, Any] | None = None


@router.post("/ingest")
async def ingest_data(req: IngestRequest):
    try:
        ds = DataSource(req.data_source)
    except ValueError:
        ds = DataSource.MES
    try:
        df = DataFormat(req.data_format)
    except ValueError:
        df = DataFormat.PARQUET

    job = _lake_service.ingest_data(
        tenant_id=req.tenant_id,
        data_source=ds,
        data_format=df,
        query=req.query,
    )
    return {"data": job.to_dict()}


@router.post("/transform")
async def transform_data(req: TransformRequest):
    job = _lake_service.transform_data(
        tenant_id=req.tenant_id,
        source_job_id=req.source_job_id,
        transformation=req.transformation,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Source job not found")
    return {"data": job.to_dict()}


@router.post("/export")
async def export_data(req: ExportRequest):
    try:
        ef = DataFormat(req.export_format)
    except ValueError:
        ef = DataFormat.CSV

    job = _lake_service.export_data(
        tenant_id=req.tenant_id,
        source_job_id=req.source_job_id,
        export_format=ef,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Source job not found")
    return {"data": job.to_dict()}


@router.post("/analyze")
async def analyze_data(req: AnalyzeRequest):
    try:
        ds = DataSource(req.data_source)
    except ValueError:
        ds = DataSource.MES

    job = _lake_service.analyze_data(
        tenant_id=req.tenant_id,
        data_source=ds,
        analysis_type=req.analysis_type,
    )
    return {"data": job.to_dict()}


@router.get("/jobs")
async def list_jobs(tenant_id: str):
    jobs = _lake_service.list_jobs(tenant_id)
    return {"data": [j.to_dict() for j in jobs]}


# --- AI Training APIs ---

@router.post("/datasets")
async def create_dataset(req: CreateDatasetRequest):
    dataset = _ai_service.create_dataset(
        tenant_id=req.tenant_id,
        name=req.name,
        dataset_type=req.dataset_type,
        data_sources=req.data_sources,
    )
    return {"data": dataset.to_dict()}


@router.get("/datasets")
async def list_datasets(tenant_id: str):
    datasets = _ai_service.list_datasets(tenant_id)
    return {"data": [d.to_dict() for d in datasets]}


@router.post("/training")
async def start_training(req: StartTrainingRequest):
    job = _ai_service.start_training(
        tenant_id=req.tenant_id,
        dataset_id=req.dataset_id,
        model_type=req.model_type,
        objective=req.objective,
        hyperparameters=req.hyperparameters,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"data": job.to_dict()}


@router.get("/training")
async def list_training_jobs(tenant_id: str):
    jobs = _ai_service.list_training_jobs(tenant_id)
    return {"data": [j.to_dict() for j in jobs]}