from __future__ import annotations

import pytest

from src.domain.services.twin_domain_service import TwinDomainService
from src.domain.services.maintenance_twin_service import (
    MaintenanceContent,
    MaintenanceResult,
    MaintenanceTwinService,
    MaintenanceType,
)


@pytest.fixture
def mtn_service():
    twin_service = TwinDomainService()
    return MaintenanceTwinService(twin_service)


class TestRecordMaintenance:
    def test_record_preventive_maintenance(self, mtn_service):
        record = mtn_service.record_maintenance(
            aircraft_sn="SN-MTN-001",
            maintenance_type=MaintenanceType.PREVENTIVE,
            content=MaintenanceContent.INSPECTION,
            result=MaintenanceResult.COMPLETED,
            component_id="landing_gear",
            component_name="Landing Gear",
            performed_by="technician",
            flight_hours=10000.0,
        )
        assert record.record_id.startswith("MR-")
        assert record.maintenance_type == MaintenanceType.PREVENTIVE
        assert record.result == MaintenanceResult.COMPLETED

    def test_record_corrective_with_parts_replaced(self, mtn_service):
        record = mtn_service.record_maintenance(
            aircraft_sn="SN-MTN-002",
            maintenance_type=MaintenanceType.CORRECTIVE,
            content=MaintenanceContent.PART_REPLACEMENT,
            result=MaintenanceResult.COMPLETED,
            component_id="hydraulic_system",
            parts_replaced=["hydraulic_pump", "seal_kit"],
            flight_hours=15000.0,
        )
        assert len(record.parts_replaced) == 2

    def test_multiple_records_for_same_aircraft(self, mtn_service):
        mtn_service.record_maintenance("SN-MTN-003", MaintenanceType.PREVENTIVE, MaintenanceContent.INSPECTION, MaintenanceResult.COMPLETED)
        mtn_service.record_maintenance("SN-MTN-003", MaintenanceType.CORRECTIVE, MaintenanceContent.DEFECT_REPAIR, MaintenanceResult.COMPLETED)

        records = mtn_service.get_maintenance_records("SN-MTN-003")
        assert len(records) == 2


class TestEstimateRemainingLife:
    def test_estimate_with_no_maintenance(self, mtn_service):
        estimates = mtn_service.estimate_remaining_life("SN-LIFE-001", flight_hours=20000.0)
        assert len(estimates) > 0
        for est in estimates:
            assert est.estimated_remaining_fh >= 0
            assert est.fatigue_damage >= 0

    def test_estimate_with_maintenance_benefit(self, mtn_service):
        mtn_service.record_maintenance(
            "SN-LIFE-002", MaintenanceType.CORRECTIVE,
            MaintenanceContent.PART_REPLACEMENT, MaintenanceResult.COMPLETED,
            component_id="landing_gear", flight_hours=10000.0,
        )
        estimates_with_mtn = mtn_service.estimate_remaining_life("SN-LIFE-002", flight_hours=15000.0)

        mtn_service2 = MaintenanceTwinService(TwinDomainService())
        estimates_without = mtn_service2.estimate_remaining_life("SN-LIFE-002-NO", flight_hours=15000.0)

        lg_with = next((e for e in estimates_with_mtn if e.component_id == "landing_gear"), None)
        lg_without = next((e for e in estimates_without if e.component_id == "landing_gear"), None)

        if lg_with and lg_without:
            assert lg_with.maintenance_benefit > lg_without.maintenance_benefit

    def test_estimate_with_health_assessments(self, mtn_service):
        estimates = mtn_service.estimate_remaining_life(
            "SN-LIFE-003",
            flight_hours=30000.0,
            health_assessments=[
                {"component_id": "wing", "fatigue_damage_cumulative": 0.5},
            ],
        )
        wing_est = next((e for e in estimates if e.component_id == "wing"), None)
        assert wing_est is not None
        assert wing_est.confidence == "high"


class TestGenerateMaintenancePlan:
    def test_preventive_plan_from_intervals(self, mtn_service):
        plan = mtn_service.generate_maintenance_plan("SN-PLAN-001", flight_hours=9000.0)
        assert len(plan) > 0
        preventive = [p for p in plan if p.maintenance_type == MaintenanceType.PREVENTIVE]
        assert len(preventive) > 0

    def test_plan_from_health_assessments(self, mtn_service):
        plan = mtn_service.generate_maintenance_plan(
            "SN-PLAN-002",
            flight_hours=50000.0,
            health_assessments=[
                {"component_id": "wing", "component_name": "Wing", "health_status": "warning"},
                {"component_id": "fuselage", "component_name": "Fuselage", "health_status": "critical"},
            ],
        )
        condition_based = [p for p in plan if p.trigger_reason == "health_assessment"]
        assert len(condition_based) > 0

    def test_plan_from_anomalies(self, mtn_service):
        plan = mtn_service.generate_maintenance_plan(
            "SN-PLAN-003",
            flight_hours=10000.0,
            anomalies=[
                {"sensor_id": "temp_s1", "metric_name": "temperature", "anomaly_type": "sensor_out_of_range", "severity": "critical"},
            ],
        )
        corrective = [p for p in plan if p.maintenance_type == MaintenanceType.CORRECTIVE]
        assert len(corrective) > 0