from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.data_lake_job import (
    AITrainingDataset,
    AITrainingJob,
    DataFormat,
    DataLakeJob,
    DataSource,
    JobType,
)


class DataLakeService:
    def __init__(self) -> None:
        self._jobs: dict[str, DataLakeJob] = {}

    def ingest_data(
        self,
        tenant_id: str,
        data_source: DataSource,
        data_format: DataFormat = DataFormat.PARQUET,
        query: str = "",
    ) -> DataLakeJob:
        job = DataLakeJob(
            tenant_id=tenant_id,
            job_type=JobType.INGEST,
            data_source=data_source,
            data_format=data_format,
        )
        job.query = query
        job.start()

        records = random.randint(1000, 100000)
        location = f"minio://aeroforge-datalake/{tenant_id}/{data_source.value}/{job.id}.{data_format.value}"
        job.complete(location, records)

        self._jobs[job.id] = job
        return job

    def transform_data(
        self,
        tenant_id: str,
        source_job_id: str,
        transformation: str = "normalize",
    ) -> DataLakeJob | None:
        source = self._jobs.get(source_job_id)
        if not source:
            return None

        job = DataLakeJob(
            tenant_id=tenant_id,
            job_type=JobType.TRANSFORM,
            data_source=source.data_source,
            data_format=DataFormat.PARQUET,
        )
        job.query = f"TRANSFORM {source_job_id} USING {transformation}"
        job.start()

        records = int(source.records_processed * random.uniform(0.8, 1.0))
        location = f"minio://aeroforge-datalake/{tenant_id}/transformed/{job.id}.parquet"
        job.complete(location, records)

        self._jobs[job.id] = job
        return job

    def export_data(
        self,
        tenant_id: str,
        source_job_id: str,
        export_format: DataFormat = DataFormat.CSV,
    ) -> DataLakeJob | None:
        source = self._jobs.get(source_job_id)
        if not source:
            return None

        job = DataLakeJob(
            tenant_id=tenant_id,
            job_type=JobType.EXPORT,
            data_source=source.data_source,
            data_format=export_format,
        )
        job.start()

        location = f"minio://aeroforge-datalake/{tenant_id}/exports/{job.id}.{export_format.value}"
        job.complete(location, source.records_processed)

        self._jobs[job.id] = job
        return job

    def analyze_data(
        self,
        tenant_id: str,
        data_source: DataSource,
        analysis_type: str = "correlation",
    ) -> DataLakeJob:
        job = DataLakeJob(
            tenant_id=tenant_id,
            job_type=JobType.ANALYZE,
            data_source=data_source,
            data_format=DataFormat.JSON,
        )
        job.query = f"ANALYZE {data_source.value} TYPE {analysis_type}"
        job.start()

        records = random.randint(100, 10000)
        location = f"minio://aeroforge-datalake/{tenant_id}/analysis/{job.id}.json"
        job.complete(location, records)

        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> DataLakeJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self, tenant_id: str) -> list[DataLakeJob]:
        return [j for j in self._jobs.values() if j.tenant_id == tenant_id]


class AITrainingPlatformService:
    def __init__(self) -> None:
        self._datasets: dict[str, AITrainingDataset] = {}
        self._training_jobs: dict[str, AITrainingJob] = {}

    def create_dataset(
        self,
        tenant_id: str,
        name: str,
        dataset_type: str = "quality_prediction",
        data_sources: list[str] | None = None,
    ) -> AITrainingDataset:
        dataset = AITrainingDataset(
            tenant_id=tenant_id,
            name=name,
            dataset_type=dataset_type,
        )
        dataset.data_sources = data_sources or ["mes", "qms"]
        dataset.record_count = random.randint(5000, 100000)
        dataset.feature_count = random.randint(10, 50)
        dataset.storage_path = f"minio://aeroforge-datalake/{tenant_id}/datasets/{dataset.id}"

        self._datasets[dataset.id] = dataset
        return dataset

    def start_training(
        self,
        tenant_id: str,
        dataset_id: str,
        model_type: str = "xgboost",
        objective: str = "quality_prediction",
        hyperparameters: dict[str, Any] | None = None,
    ) -> AITrainingJob | None:
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return None

        job = AITrainingJob(
            tenant_id=tenant_id,
            dataset_id=dataset_id,
            model_type=model_type,
            objective=objective,
        )
        job.hyperparameters = hyperparameters or {
            "learning_rate": 0.1,
            "max_depth": 6,
            "n_estimators": 100,
        }
        job.start()

        metrics = {
            "accuracy": round(random.uniform(0.85, 0.97), 4),
            "precision": round(random.uniform(0.83, 0.95), 4),
            "recall": round(random.uniform(0.80, 0.94), 4),
            "f1_score": round(random.uniform(0.82, 0.95), 4),
        }
        model_path = f"minio://aeroforge-datalake/{tenant_id}/models/{job.id}.pkl"
        job.complete(metrics, model_path)

        self._training_jobs[job.id] = job
        return job

    def get_dataset(self, dataset_id: str) -> AITrainingDataset | None:
        return self._datasets.get(dataset_id)

    def get_training_job(self, job_id: str) -> AITrainingJob | None:
        return self._training_jobs.get(job_id)

    def list_datasets(self, tenant_id: str) -> list[AITrainingDataset]:
        return [d for d in self._datasets.values() if d.tenant_id == tenant_id]

    def list_training_jobs(self, tenant_id: str) -> list[AITrainingJob]:
        return [j for j in self._training_jobs.values() if j.tenant_id == tenant_id]