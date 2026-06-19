"""AeroForge-X V6.0/V6.1 Unit Tests - NDTIntegrationService
REQ-SUP-013~018, REQ-VP-020
"""

import pytest

from src.domain.services.supplier.ndt_integration_service import (
    NDTIntegrationService,
    NDTRecord,
    NDTMethod,
    NDTResult,
    NDTFilter,
    NDTStatistics,
    FRACASLinkResult,
)


@pytest.fixture
def service():
    return NDTIntegrationService()


@pytest.fixture
def accept_record():
    return NDTRecord(
        ndt_id="NDT-001",
        part_id="PART-A",
        inspection_method=NDTMethod.UT,
        result=NDTResult.ACCEPT,
        linked_lot_id="SUP-001-LOT",
    )


@pytest.fixture
def reject_record():
    return NDTRecord(
        ndt_id="NDT-002",
        part_id="PART-B",
        inspection_method=NDTMethod.RT,
        result=NDTResult.REJECT,
        linked_lot_id="SUP-002-LOT",
        defects_found=[{"defect_type": "Crack", "location": "Wing root"}],
    )


@pytest.fixture
def conditional_record():
    return NDTRecord(
        ndt_id="NDT-003",
        part_id="PART-C",
        inspection_method=NDTMethod.PT,
        result=NDTResult.CONDITIONAL,
        linked_lot_id="SUP-001-LOT",
    )


class TestImportNDTRecord:

    def test_import_accept_record(self, service, accept_record):
        result = service.importNDTRecord(accept_record)
        assert result.ndt_id == "NDT-001"
        assert result.result == NDTResult.ACCEPT

    def test_import_reject_triggers_fracas(self, service, reject_record):
        result = service.importNDTRecord(reject_record)
        assert result.result == NDTResult.REJECT

    def test_import_conditional_triggers_review(self, service, conditional_record):
        result = service.importNDTRecord(conditional_record)
        assert result.result == NDTResult.CONDITIONAL

    def test_import_duplicate_raises(self, service, accept_record):
        service.importNDTRecord(accept_record)
        with pytest.raises(ValueError, match="already exists"):
            service.importNDTRecord(accept_record)


class TestRejectHandling:

    def test_handle_reject_result(self, service, reject_record):
        service.importNDTRecord(reject_record)
        result = service.handleRejectResult("NDT-002")
        assert isinstance(result, FRACASLinkResult)
        assert result.fracas_report_id.startswith("FRACAS-NDT-")
        assert result.disposition_process_started is True

    def test_handle_reject_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.handleRejectResult("FAKE-NDT")


class TestConditionalHandling:

    def test_handle_conditional_result(self, service, conditional_record):
        service.importNDTRecord(conditional_record)
        result = service.handleConditionalResult("NDT-003")
        assert result["flagged_for_review"] is True
        assert result["review_status"] == "PendingEngineeringReview"

    def test_resolve_conditional_result(self, service, conditional_record):
        service.importNDTRecord(conditional_record)
        result = service.resolveConditionalResult("NDT-003", "AcceptWithDeviation")
        assert result["disposition_decision"] == "AcceptWithDeviation"
        assert result["status"] == "Resolved"

    def test_resolve_nonexistent_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.resolveConditionalResult("FAKE-NDT", "Accept")


class TestStatistics:

    def test_compute_statistics(self, service, accept_record, reject_record, conditional_record):
        service.importNDTRecord(accept_record)
        service.importNDTRecord(reject_record)
        service.importNDTRecord(conditional_record)
        stats = service.computeNDTStatistics()
        assert isinstance(stats, NDTStatistics)
        assert stats.total_records == 3
        assert stats.accept_count == 1
        assert stats.reject_count == 1
        assert stats.conditional_count == 1

    def test_filter_by_method(self, service, accept_record, reject_record):
        service.importNDTRecord(accept_record)
        service.importNDTRecord(reject_record)
        stats = service.computeNDTStatistics(NDTFilter(method=NDTMethod.UT))
        assert stats.total_records == 1

    def test_filter_by_result(self, service, accept_record, reject_record):
        service.importNDTRecord(accept_record)
        service.importNDTRecord(reject_record)
        stats = service.computeNDTStatistics(NDTFilter(result=NDTResult.REJECT))
        assert stats.total_records == 1
        assert stats.reject_count == 1

    def test_method_effectiveness(self, service, accept_record, reject_record):
        service.importNDTRecord(accept_record)
        service.importNDTRecord(reject_record)
        stats = service.computeNDTStatistics()
        assert "UT" in stats.method_effectiveness
        assert "RT" in stats.method_effectiveness


class TestGetRecord:

    def test_get_existing_record(self, service, accept_record):
        service.importNDTRecord(accept_record)
        result = service.getRecord("NDT-001")
        assert result is not None

    def test_get_nonexistent_returns_none(self, service):
        result = service.getRecord("FAKE-NDT")
        assert result is None