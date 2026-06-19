"""AeroForge-X V6.1 Unit Tests - DatasetVersioningService
REQ-DG-001~004, REQ-VP-020
"""

import pytest

from src.domain.services.data_governance.dataset_versioning_service import (
    DatasetVersioningService,
    DatasetVersion,
    DatasetFingerprint,
    DatasetDeltaReport,
    ModelDatasetLink,
)


@pytest.fixture
def service():
    return DatasetVersioningService()


class TestCreateDatasetVersion:

    def test_create_version(self, service):
        v = service.createDatasetVersion(
            dataset_id="CFD-001", major=1, minor=0, patch=0,
            source="ANSYS-Fluent", sample_count=10000,
        )
        assert isinstance(v, DatasetVersion)
        assert v.dataset_version_id == "DSV-CFD-001-1.0.0"
        assert v.version_string() == "1.0.0"

    def test_create_multiple_versions(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        service.createDatasetVersion("CFD-001", 1, 1, 0)
        versions = service.getVersionsByDataset("CFD-001")
        assert len(versions) == 2

    def test_create_duplicate_version_raises(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        with pytest.raises(ValueError, match="already exists"):
            service.createDatasetVersion("CFD-001", 1, 0, 0)


class TestComputeFingerprint:

    def test_compute_fingerprint(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        fp = service.computeDatasetFingerprint(
            "DSV-CFD-001-1.0.0",
            {"CL": [0.5, 0.51, 0.49, 0.50, 0.52], "CD": [0.02, 0.021, 0.019, 0.020, 0.022]},
        )
        assert isinstance(fp, DatasetFingerprint)
        assert "CL" in fp.feature_statistics
        assert "mean" in fp.feature_statistics["CL"]

    def test_fingerprint_stored_on_version(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        service.computeDatasetFingerprint("DSV-CFD-001-1.0.0", {"CL": [0.5, 0.51]})
        v = service.getVersion("DSV-CFD-001-1.0.0")
        assert v.fingerprint is not None

    def test_compute_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.computeDatasetFingerprint("FAKE-ID", {"CL": [0.5]})


class TestCompareVersions:

    def test_compare_versions(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0, sample_count=100,
                                     feature_schema={"CL": "float", "CD": "float"})
        service.createDatasetVersion("CFD-001", 1, 1, 0, sample_count=150,
                                     feature_schema={"CL": "float", "CD": "float", "CM": "float"})
        delta = service.compareDatasetVersions("DSV-CFD-001-1.0.0", "DSV-CFD-001-1.1.0")
        assert isinstance(delta, DatasetDeltaReport)
        assert delta.added_samples == 50
        assert len(delta.schema_changes) > 0

    def test_compare_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.compareDatasetVersions("FAKE-1", "FAKE-2")


class TestLinkModelToDataset:

    def test_link_model(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        link = service.linkModelToDataset("SM-001", "DSV-CFD-001-1.0.0")
        assert isinstance(link, ModelDatasetLink)
        assert link.model_id == "SM-001"

    def test_link_duplicate_returns_existing(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        link1 = service.linkModelToDataset("SM-001", "DSV-CFD-001-1.0.0")
        link2 = service.linkModelToDataset("SM-001", "DSV-CFD-001-1.0.0")
        assert link1.link_id == link2.link_id

    def test_link_nonexistent_dataset_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.linkModelToDataset("SM-001", "FAKE-DSV")

    def test_get_links_by_model(self, service):
        service.createDatasetVersion("CFD-001", 1, 0, 0)
        service.linkModelToDataset("SM-001", "DSV-CFD-001-1.0.0")
        links = service.getLinksByModel("SM-001")
        assert len(links) == 1