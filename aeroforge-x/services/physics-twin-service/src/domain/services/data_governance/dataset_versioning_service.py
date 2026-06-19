"""AeroForge-X V6.1 DatasetVersioningService

CFD training dataset semantic version management:
version creation, fingerprint computation, incremental comparison,
and model-dataset linkage.

REQ-DG-001~004
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatasetFingerprint:
    dataset_version_id: str
    feature_statistics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "dataset_version_id": self.dataset_version_id,
            "feature_statistics": self.feature_statistics,
        }


@dataclass
class DatasetVersion:
    dataset_version_id: str
    dataset_id: str
    major: int = 1
    minor: int = 0
    patch: int = 0
    source: str = ""
    sample_count: int = 0
    feature_schema: dict = field(default_factory=dict)
    change_summary: str = ""
    fingerprint: Optional[DatasetFingerprint] = None
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "dataset_version_id": self.dataset_version_id,
            "dataset_id": self.dataset_id,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "source": self.source,
            "sample_count": self.sample_count,
            "feature_schema": self.feature_schema,
            "change_summary": self.change_summary,
            "fingerprint": self.fingerprint.to_dict() if self.fingerprint else None,
            "created_at": self.created_at,
        }

    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass
class DatasetDeltaReport:
    source_version_id: str
    target_version_id: str
    added_samples: int = 0
    removed_samples: int = 0
    modified_samples: int = 0
    schema_changes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_version_id": self.source_version_id,
            "target_version_id": self.target_version_id,
            "added_samples": self.added_samples,
            "removed_samples": self.removed_samples,
            "modified_samples": self.modified_samples,
            "schema_changes": self.schema_changes,
        }


@dataclass
class ModelDatasetLink:
    link_id: str
    model_id: str
    dataset_version_id: str
    linked_at: str = ""

    def to_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "model_id": self.model_id,
            "dataset_version_id": self.dataset_version_id,
            "linked_at": self.linked_at,
        }


class DatasetVersioningService:

    def __init__(self) -> None:
        self._versions: dict[str, DatasetVersion] = {}
        self._links: dict[str, ModelDatasetLink] = {}

    def createDatasetVersion(
        self,
        dataset_id: str,
        major: int = 1,
        minor: int = 0,
        patch: int = 0,
        source: str = "",
        sample_count: int = 0,
        feature_schema: dict | None = None,
        change_summary: str = "",
    ) -> DatasetVersion:
        version_id = f"DSV-{dataset_id}-{major}.{minor}.{patch}"

        for existing in self._versions.values():
            if existing.dataset_id == dataset_id and existing.major == major and existing.minor == minor and existing.patch == patch:
                raise ValueError(f"Dataset version {major}.{minor}.{patch} already exists for {dataset_id}")

        version = DatasetVersion(
            dataset_version_id=version_id,
            dataset_id=dataset_id,
            major=major,
            minor=minor,
            patch=patch,
            source=source,
            sample_count=sample_count,
            feature_schema=feature_schema or {},
            change_summary=change_summary,
        )
        self._versions[version_id] = version
        return version

    def computeDatasetFingerprint(
        self, dataset_version_id: str, feature_data: dict[str, list[float]]
    ) -> DatasetFingerprint:
        version = self._versions.get(dataset_version_id)
        if version is None:
            raise ValueError(f"Dataset version not found: {dataset_version_id}")

        import numpy as np

        stats = {}
        for feature_name, values in feature_data.items():
            arr = np.array(values, dtype=float)
            if len(arr) > 0:
                stats[feature_name] = {
                    "mean": float(np.mean(arr)),
                    "std": float(np.std(arr)),
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "p25": float(np.percentile(arr, 25)),
                    "p50": float(np.percentile(arr, 50)),
                    "p75": float(np.percentile(arr, 75)),
                }
            else:
                stats[feature_name] = {
                    "mean": 0.0, "std": 0.0, "min": 0.0,
                    "max": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0,
                }

        fingerprint = DatasetFingerprint(
            dataset_version_id=dataset_version_id,
            feature_statistics=stats,
        )
        version.fingerprint = fingerprint
        return fingerprint

    def compareDatasetVersions(
        self, source_version_id: str, target_version_id: str
    ) -> DatasetDeltaReport:
        source = self._versions.get(source_version_id)
        target = self._versions.get(target_version_id)
        if source is None or target is None:
            raise ValueError("One or both dataset versions not found")

        source_features = set(source.feature_schema.keys()) if source.feature_schema else set()
        target_features = set(target.feature_schema.keys()) if target.feature_schema else set()

        schema_changes = []
        added = target_features - source_features
        removed = source_features - target_features
        for f in added:
            schema_changes.append({"feature": f, "change": "added"})
        for f in removed:
            schema_changes.append({"feature": f, "change": "removed"})

        delta_samples = target.sample_count - source.sample_count

        return DatasetDeltaReport(
            source_version_id=source_version_id,
            target_version_id=target_version_id,
            added_samples=max(0, delta_samples),
            removed_samples=max(0, -delta_samples),
            modified_samples=0,
            schema_changes=schema_changes,
        )

    def linkModelToDataset(
        self, model_id: str, dataset_version_id: str
    ) -> ModelDatasetLink:
        if dataset_version_id not in self._versions:
            raise ValueError(f"Dataset version not found: {dataset_version_id}")

        link_id = f"MDL-{uuid.uuid4().hex[:8]}"
        for existing in self._links.values():
            if existing.model_id == model_id and existing.dataset_version_id == dataset_version_id:
                return existing

        link = ModelDatasetLink(
            link_id=link_id,
            model_id=model_id,
            dataset_version_id=dataset_version_id,
        )
        self._links[link_id] = link
        return link

    def getVersion(self, version_id: str) -> Optional[DatasetVersion]:
        return self._versions.get(version_id)

    def getVersionsByDataset(self, dataset_id: str) -> list[DatasetVersion]:
        return [v for v in self._versions.values() if v.dataset_id == dataset_id]

    def getLinksByModel(self, model_id: str) -> list[ModelDatasetLink]:
        return [l for l in self._links.values() if l.model_id == model_id]