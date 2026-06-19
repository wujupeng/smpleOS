"""AeroForge-X V6.1 Dataset Governance API

RESTful endpoints for CFD Dataset Manager:
dataset versioning, drift detection, quality scoring.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.domain.services.data_governance.dataset_versioning_service import (
    DatasetVersioningService,
)
from src.domain.services.data_governance.dataset_drift_detection_service import (
    DatasetDriftDetectionService,
)
from src.domain.services.data_governance.dataset_quality_score_service import (
    DatasetQualityScoreService,
)

router = APIRouter(prefix="/api/v6/physics-twin/datasets", tags=["v6-datasets"])

_versioning_svc = DatasetVersioningService()
_drift_svc = DatasetDriftDetectionService()
_quality_svc = DatasetQualityScoreService()


@router.post("/versions")
async def create_dataset_version(body: dict):
    version = _versioning_svc.createDatasetVersion(
        dataset_id=body.get("dataset_id", ""),
        major=body.get("major", 1),
        minor=body.get("minor", 0),
        patch=body.get("patch", 0),
        source=body.get("source", ""),
        sample_count=body.get("sample_count", 0),
        feature_schema=body.get("feature_schema"),
        change_summary=body.get("change_summary", ""),
    )
    return version.to_dict()


@router.post("/versions/{version_id}/fingerprint")
async def compute_fingerprint(version_id: str, body: dict):
    feature_data = body.get("feature_data", {})
    fingerprint = _versioning_svc.computeDatasetFingerprint(version_id, feature_data)
    return fingerprint.to_dict()


@router.post("/versions/compare")
async def compare_versions(body: dict):
    report = _versioning_svc.compareDatasetVersions(
        source_version_id=body.get("source_version_id", ""),
        target_version_id=body.get("target_version_id", ""),
    )
    return report.to_dict()


@router.post("/model-dataset-links")
async def link_model_to_dataset(body: dict):
    link = _versioning_svc.linkModelToDataset(
        model_id=body.get("model_id", ""),
        dataset_version_id=body.get("dataset_version_id", ""),
    )
    return link.to_dict()


@router.post("/drift/feature")
async def detect_feature_drift(body: dict):
    result = _drift_svc.detectFeatureDrift(
        dataset_id=body.get("dataset_id", ""),
        reference_dataset_id=body.get("reference_dataset_id", ""),
        reference_data=body.get("reference_data", {}),
        current_data=body.get("current_data", {}),
        alpha=body.get("alpha"),
    )
    return result.to_dict()


@router.post("/drift/concept")
async def detect_concept_drift(body: dict):
    result = _drift_svc.detectConceptDrift(
        dataset_id=body.get("dataset_id", ""),
        reference_dataset_id=body.get("reference_dataset_id", ""),
        baseline_errors=body.get("baseline_errors", []),
        current_errors=body.get("current_errors", []),
        threshold_sigma=body.get("threshold_sigma"),
    )
    return result.to_dict()


@router.post("/drift/psi")
async def compute_psi(body: dict):
    result = _drift_svc.computePSI(
        dataset_id=body.get("dataset_id", ""),
        reference_dataset_id=body.get("reference_dataset_id", ""),
        reference_data=body.get("reference_data", {}),
        current_data=body.get("current_data", {}),
        n_bins=body.get("n_bins", 10),
    )
    return result.to_dict()


@router.get("/drift/{dataset_id}/history")
async def get_drift_history(dataset_id: str, limit: int = 100):
    entries = _drift_svc.getDriftHistory(dataset_id, limit)
    return [e.to_dict() for e in entries]


@router.post("/quality/score")
async def compute_quality_score(body: dict):
    assessment = _quality_svc.computeQualityScore(
        dataset_id=body.get("dataset_id", ""),
        missing_value_ratio=body.get("missing_value_ratio", 0.0),
        constraint_violation_ratio=body.get("constraint_violation_ratio", 0.0),
        data_age_days=body.get("data_age_days", 0.0),
        max_acceptable_age_days=body.get("max_acceptable_age_days", 365.0),
        design_space_coverage=body.get("design_space_coverage", 1.0),
    )
    return assessment.to_dict()


@router.post("/quality/inflate-uq")
async def inflate_uq_uncertainty(body: dict):
    inflated = _quality_svc.inflateUQUncertainty(
        base_uncertainty=body.get("base_uncertainty", 0.05),
        quality_score=body.get("quality_score", 100.0),
    )
    return {"inflated_uncertainty": inflated}


@router.get("/quality/{dataset_id}/assessments")
async def get_quality_assessments(dataset_id: str, limit: int = 100):
    assessments = _quality_svc.getAssessments(dataset_id, limit)
    return [a.to_dict() for a in assessments]