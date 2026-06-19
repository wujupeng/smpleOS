from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class JobType(str, Enum):
    INGEST = "ingest"
    TRANSFORM = "transform"
    EXPORT = "export"
    ANALYZE = "analyze"


class DataSource(str, Enum):
    DESIGN = "design"
    ENGINEERING = "engineering"
    CAE = "cae"
    PLM = "plm"
    BOM = "bom"
    MES = "mes"
    QMS = "qms"
    TWIN = "twin"
    SUPPLY_CHAIN = "supply_chain"


class DataFormat(str, Enum):
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"
    AVRO = "avro"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DataLakeJob(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        job_type: JobType,
        data_source: DataSource,
        data_format: DataFormat = DataFormat.PARQUET,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.job_type = job_type
        self.data_source = data_source
        self.data_format = data_format
        self.query: str = ""
        self.status = JobStatus.PENDING
        self.result_location: str = ""
        self.records_processed: int = 0
        self.error_message: str = ""
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def start(self) -> None:
        self.status = JobStatus.RUNNING

    def complete(self, result_location: str, records: int) -> None:
        self.status = JobStatus.COMPLETED
        self.result_location = result_location
        self.records_processed = records
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error_message = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "job_type": self.job_type.value,
            "data_source": self.data_source.value,
            "data_format": self.data_format.value,
            "status": self.status.value,
            "records_processed": self.records_processed,
            "result_location": self.result_location,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AITrainingDataset(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        name: str,
        dataset_type: str = "quality_prediction",
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.name = name
        self.dataset_type = dataset_type
        self.data_sources: list[str] = []
        self.record_count: int = 0
        self.feature_count: int = 0
        self.version: int = 1
        self.storage_path: str = ""
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "dataset_type": self.dataset_type,
            "data_sources": self.data_sources,
            "record_count": self.record_count,
            "feature_count": self.feature_count,
            "version": self.version,
            "storage_path": self.storage_path,
            "created_at": self.created_at.isoformat(),
        }


class AITrainingJob(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        dataset_id: str,
        model_type: str = "xgboost",
        objective: str = "quality_prediction",
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.dataset_id = dataset_id
        self.model_type = model_type
        self.objective = objective
        self.hyperparameters: dict[str, Any] = {}
        self.metrics: dict[str, float] = {}
        self.model_path: str = ""
        self.status = JobStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None

    def start(self) -> None:
        self.status = JobStatus.RUNNING

    def complete(self, metrics: dict[str, float], model_path: str) -> None:
        self.status = JobStatus.COMPLETED
        self.metrics = metrics
        self.model_path = model_path
        self.completed_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        self.status = JobStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "dataset_id": self.dataset_id,
            "model_type": self.model_type,
            "objective": self.objective,
            "hyperparameters": self.hyperparameters,
            "metrics": self.metrics,
            "model_path": self.model_path,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }