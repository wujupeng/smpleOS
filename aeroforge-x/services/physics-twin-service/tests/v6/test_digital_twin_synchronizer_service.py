"""AeroForge-X V6.0/V6.1 Unit Tests - DigitalTwinSynchronizerService
REQ-FACTORY-007~012, REQ-VP-020
"""

import pytest

from src.domain.services.digital_factory.digital_twin_synchronizer_service import (
    DigitalTwinSynchronizerService,
    DeviationAlert,
    DeviationRootCause,
    TwinCommand,
    TwinSyncResult,
    CommandResult,
    SafetyVerificationResult,
)


@pytest.fixture
def service():
    return DigitalTwinSynchronizerService()


class TestSyncTwinState:

    def test_sync_synchronized_states(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0, "pressure": 50.0})
        service.updatePhysicalState("EQ-001", {"temp": 100.0, "pressure": 50.0})
        result = service.syncTwinState("EQ-001")
        assert isinstance(result, TwinSyncResult)
        assert result.is_synchronized is True

    def test_sync_deviated_states(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 120.0})
        result = service.syncTwinState("EQ-001")
        assert result.is_synchronized is False
        assert len(result.deviation_items) > 0

    def test_sync_empty_states(self, service):
        result = service.syncTwinState("EQ-001")
        assert result.is_synchronized is True

    def test_sync_log_recorded(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 100.0})
        service.syncTwinState("EQ-001")
        log = service.getSyncAuditLog()
        assert len(log) == 1


class TestDetectDeviation:

    def test_detect_no_deviation(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 101.0})
        result = service.detectDeviation("EQ-001")
        assert result is None

    def test_detect_significant_deviation(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 120.0})
        result = service.detectDeviation("EQ-001")
        assert isinstance(result, DeviationAlert)
        assert result.deviation_percentage > 5.0

    def test_detect_sensor_error_root_cause(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 200.0})
        result = service.detectDeviation("EQ-001")
        assert result.root_cause == DeviationRootCause.SENSOR_ERROR

    def test_detect_process_drift_root_cause(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 130.0})
        result = service.detectDeviation("EQ-001")
        assert result.root_cause == DeviationRootCause.PROCESS_DRIFT

    def test_detect_equipment_degradation_root_cause(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 108.0})
        result = service.detectDeviation("EQ-001")
        assert result.root_cause == DeviationRootCause.EQUIPMENT_DEGRADATION

    def test_deviation_has_corrective_action(self, service):
        service.updateTwinState("EQ-001", {"temp": 100.0})
        service.updatePhysicalState("EQ-001", {"temp": 120.0})
        result = service.detectDeviation("EQ-001")
        assert result.suggested_corrective_action != ""


class TestIssueTwinCommand:

    def test_issue_verified_command(self, service):
        cmd = TwinCommand(
            command_id="CMD-001",
            command_type="AdjustTemperature",
            parameters={"temperature": 150},
            authorized_by_production="prod-1",
            authorized_by_safety="safety-1",
            safety_verified=True,
        )
        result = service.issueTwinCommand(cmd)
        assert isinstance(result, CommandResult)
        assert result.executed is True

    def test_issue_unverified_command_rejected(self, service):
        cmd = TwinCommand(
            command_id="CMD-002",
            command_type="AdjustTemperature",
            parameters={"temperature": 150},
            safety_verified=False,
        )
        result = service.issueTwinCommand(cmd)
        assert result.executed is False
        assert "safety-verified" in result.error

    def test_issue_command_without_dual_auth(self, service):
        cmd = TwinCommand(
            command_id="CMD-003",
            command_type="AdjustTemperature",
            parameters={"temperature": 150},
            authorized_by_production="prod-1",
            safety_verified=True,
        )
        result = service.issueTwinCommand(cmd)
        assert result.executed is False
        assert "Dual authorization" in result.error


class TestVerifyCommandSafety:

    def test_verify_safe_command(self, service):
        cmd = TwinCommand(
            command_id="CMD-001",
            command_type="AdjustTemperature",
            parameters={"temperature": 200},
            authorized_by_safety="safety-1",
        )
        result = service.verifyCommandSafety(cmd)
        assert isinstance(result, SafetyVerificationResult)
        assert result.is_safe is True

    def test_verify_unsafe_temperature(self, service):
        cmd = TwinCommand(
            command_id="CMD-002",
            command_type="Overheat",
            parameters={"temperature": 1500},
            authorized_by_safety="safety-1",
        )
        result = service.verifyCommandSafety(cmd)
        assert result.is_safe is False

    def test_verify_unsafe_pressure(self, service):
        cmd = TwinCommand(
            command_id="CMD-003",
            command_type="Pressurize",
            parameters={"pressure": 600},
            authorized_by_safety="safety-1",
        )
        result = service.verifyCommandSafety(cmd)
        assert result.is_safe is False

    def test_safety_verified_flag_set(self, service):
        cmd = TwinCommand(
            command_id="CMD-004",
            command_type="Adjust",
            parameters={"temperature": 200},
            authorized_by_safety="safety-1",
        )
        service.verifyCommandSafety(cmd)
        assert cmd.safety_verified is True