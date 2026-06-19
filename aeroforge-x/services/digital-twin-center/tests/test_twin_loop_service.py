from __future__ import annotations

import pytest

from src.domain.entities.digital_twin import DigitalTwin, TwinType, SyncStatus
from src.domain.services.twin_domain_service import TwinDomainService
from src.domain.services.design_twin_service import DesignTwinService
from src.domain.services.manufacturing_twin_service import ManufacturingTwinService
from src.domain.services.twin_loop_service import (
    ConflictResolution,
    FeedbackType,
    TwinLoopService,
)


@pytest.fixture
def twin_service():
    return TwinDomainService()


@pytest.fixture
def design_twin_service(twin_service):
    return DesignTwinService(twin_service)


@pytest.fixture
def manufacturing_twin_service(twin_service):
    return ManufacturingTwinService(twin_service)


@pytest.fixture
def loop_service(twin_service, design_twin_service, manufacturing_twin_service):
    return TwinLoopService(twin_service, design_twin_service, manufacturing_twin_service)


class TestManufacturingFeedbackToDesign:
    def test_no_feedback_when_no_deviations(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-001", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.0}})

        result = loop_service.feedback_to_design("SN-001", source_type="manufacturing")
        assert result is None

    def test_feedback_generated_for_out_of_tolerance(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-002", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {
            "actual_dimensions": {"wing_span": 10.5},
            "deviations": [
                {
                    "dimension_name": "wing_span",
                    "design_value": 10.0,
                    "actual_value": 10.5,
                    "tolerance": 0.2,
                    "deviation": 0.5,
                    "is_out_of_tolerance": True,
                }
            ],
        })

        result = loop_service.feedback_to_design("SN-002", source_type="manufacturing")
        assert result is not None
        assert result.feedback_type == FeedbackType.MANUFACTURING_TO_DESIGN
        assert result.trigger_reason == "manufacturing_deviation_out_of_tolerance"
        assert "out_of_tolerance_items" in result.details

    def test_feedback_with_override_params_applied(self, loop_service, twin_service, design_twin_service):
        design_twin_service.sync_with_design("SN-003", {"wing_span": 10.0, "fuselage_length": 20.0})
        mfg_twin = twin_service.create_twin("SN-003", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.5}})

        result = loop_service.feedback_to_design(
            "SN-003",
            source_type="manufacturing",
            override_params={"wing_span": 10.5},
        )
        assert result is not None
        assert result.status == "applied"
        assert result.resolved_at is not None


class TestFlightFeedbackToDesign:
    def test_no_feedback_when_no_exceedance(self, loop_service, twin_service):
        flight_twin = twin_service.create_twin("SN-010", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"flight_loads": {"lift": 100.0}})

        result = loop_service.feedback_to_design("SN-010", source_type="flight")
        assert result is None

    def test_feedback_for_flight_load_exceedance(self, loop_service, twin_service):
        design_twin = twin_service.create_twin("SN-011", TwinType.DESIGN)
        design_twin.sync("design_sync", {"design_loads": {"lift": 100.0}})

        flight_twin = twin_service.create_twin("SN-011", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"flight_loads": {"lift": 120.0}})

        result = loop_service.feedback_to_design("SN-011", source_type="flight")
        assert result is not None
        assert result.feedback_type == FeedbackType.FLIGHT_TO_DESIGN
        assert result.trigger_reason == "flight_load_exceeded_design"

    def test_flight_feedback_with_override(self, loop_service, twin_service, design_twin_service):
        design_twin_service.sync_with_design("SN-012", {"design_loads": {"lift": 100.0}})
        flight_twin = twin_service.create_twin("SN-012", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"flight_loads": {"lift": 120.0}})

        result = loop_service.feedback_to_design(
            "SN-012",
            source_type="flight",
            override_params={"design_loads": {"lift": 125.0}},
        )
        assert result is not None
        assert result.status == "applied"


class TestFeedbackToMaintenance:
    def test_no_feedback_when_no_maintenance_impact(self, loop_service, twin_service, design_twin_service):
        design_twin_service.sync_with_design("SN-020", {"wing_span": 10.0})
        result = loop_service.feedback_to_maintenance("SN-020")
        assert result is None

    def test_feedback_for_maintenance_impacting_changes(self, loop_service, twin_service, design_twin_service):
        design_twin_service.sync_with_design("SN-021", {"wing_span": 10.0})
        design_twin_service.sync_with_design(
            "SN-021",
            {"wing_span": 10.0, "fatigue_life": 50000},
            changed_by="engineer",
            reason="fatigue_update",
        )

        result = loop_service.feedback_to_maintenance("SN-021")
        assert result is not None
        assert result.feedback_type == FeedbackType.DESIGN_TO_MAINTENANCE
        assert "maintenance_impact_params" in result.details

    def test_feedback_with_explicit_design_changes(self, loop_service, twin_service, design_twin_service):
        design_twin_service.sync_with_design("SN-022", {"wing_span": 10.0})

        result = loop_service.feedback_to_maintenance(
            "SN-022",
            design_changes={"inspection_interval": 500, "corrosion_protection": "enhanced"},
        )
        assert result is not None
        assert len(result.details["maintenance_impact_params"]) == 2


class TestConflictDetection:
    def test_no_conflict_when_data_matches(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-030", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.0}})

        flight_twin = twin_service.create_twin("SN-030", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"inferred_dimensions": {"wing_span": 10.01}})

        conflicts = loop_service.detect_conflict("SN-030")
        assert len(conflicts) == 0

    def test_conflict_detected_when_deviation_exceeds_threshold(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-031", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.0}})

        flight_twin = twin_service.create_twin("SN-031", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"inferred_dimensions": {"wing_span": 11.0}})

        conflicts = loop_service.detect_conflict("SN-031")
        assert len(conflicts) == 1
        assert conflicts[0].resolution == ConflictResolution.MANUFACTURING_WINS
        assert conflicts[0].resolved_value == 10.0
        assert conflicts[0].reason == "manufacturing_measured_data_takes_precedence"

    def test_conflict_with_custom_threshold(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-032", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.0}})

        flight_twin = twin_service.create_twin("SN-032", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"inferred_dimensions": {"wing_span": 10.03}})

        conflicts_strict = loop_service.detect_conflict("SN-032", conflict_threshold=0.001)
        assert len(conflicts_strict) == 1

    def test_conflict_with_explicit_data(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-033", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {})

        flight_twin = twin_service.create_twin("SN-033", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {})

        conflicts = loop_service.detect_conflict(
            "SN-033",
            manufacturing_data={"fuselage_length": 20.0},
            flight_data={"fuselage_length": 22.0},
        )
        assert len(conflicts) == 1
        assert conflicts[0].resolved_value == 20.0

    def test_missing_twin_types_returns_empty(self, loop_service, twin_service):
        twin_service.create_twin("SN-034", TwinType.DESIGN)
        conflicts = loop_service.detect_conflict("SN-034")
        assert len(conflicts) == 0


class TestResolveFeedbackAndConflict:
    def test_resolve_feedback(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-040", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {
            "actual_dimensions": {"wing_span": 10.5},
            "deviations": [{"dimension_name": "wing_span", "is_out_of_tolerance": True}],
        })
        record = loop_service.feedback_to_design("SN-040")
        assert record is not None

        resolved = loop_service.resolve_feedback(record.feedback_id, "approved")
        assert resolved is not None
        assert resolved.status == "approved"
        assert resolved.resolved_at is not None

    def test_resolve_conflict(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-041", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.0}})

        flight_twin = twin_service.create_twin("SN-041", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"inferred_dimensions": {"wing_span": 12.0}})

        conflicts = loop_service.detect_conflict("SN-041")
        assert len(conflicts) == 1

        resolved = loop_service.resolve_conflict(
            conflicts[0].conflict_id,
            ConflictResolution.MANUFACTURING_WINS,
        )
        assert resolved is not None
        assert resolved.resolved_value == 10.0

    def test_resolve_nonexistent_feedback(self, loop_service):
        result = loop_service.resolve_feedback("nonexistent", "approved")
        assert result is None

    def test_resolve_nonexistent_conflict(self, loop_service):
        result = loop_service.resolve_conflict("nonexistent", ConflictResolution.MANUFACTURING_WINS)
        assert result is None


class TestGetRecords:
    def test_get_feedback_records_filtered(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-050", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {
            "actual_dimensions": {"wing_span": 10.5},
            "deviations": [{"dimension_name": "wing_span", "is_out_of_tolerance": True}],
        })
        loop_service.feedback_to_design("SN-050")

        all_records = loop_service.get_feedback_records()
        assert len(all_records) >= 1

        filtered = loop_service.get_feedback_records(aircraft_sn="SN-050")
        assert len(filtered) >= 1

        type_filtered = loop_service.get_feedback_records(feedback_type=FeedbackType.MANUFACTURING_TO_DESIGN)
        assert all(r.feedback_type == FeedbackType.MANUFACTURING_TO_DESIGN for r in type_filtered)

    def test_get_conflict_records(self, loop_service, twin_service):
        mfg_twin = twin_service.create_twin("SN-051", TwinType.MANUFACTURING)
        mfg_twin.sync("measurement_sync", {"actual_dimensions": {"wing_span": 10.0}})

        flight_twin = twin_service.create_twin("SN-051", TwinType.FLIGHT)
        flight_twin.sync("flight_sync", {"inferred_dimensions": {"wing_span": 12.0}})

        loop_service.detect_conflict("SN-051")

        all_conflicts = loop_service.get_conflict_records()
        assert len(all_conflicts) >= 1

        filtered = loop_service.get_conflict_records(aircraft_sn="SN-051")
        assert len(filtered) >= 1