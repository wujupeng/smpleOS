import pytest

from services.mes_center.src.domain.entities.production_schedule import (
    ProductionSchedule, ScheduleStatus, ObjectiveFunction,
    ScheduleConstraint, ConstraintType, ConstraintPriority,
    WorkOrderSchedule, ScheduledOperation, ResourceInfo,
)
from services.mes_center.src.domain.services.scheduling_domain_service import SchedulingDomainService


class TestProductionScheduleEntity:
    def test_create_schedule(self) -> None:
        schedule = ProductionSchedule(name="Test Schedule", tenant_id="t-001")
        assert schedule.status == ScheduleStatus.DRAFT
        assert schedule.objective_function == ObjectiveFunction.MIN_MAKESPAN

    def test_schedule_to_dict(self) -> None:
        schedule = ProductionSchedule(name="Test", tenant_id="t-001", project_id="p-001")
        d = schedule.to_dict()
        assert d["name"] == "Test"
        assert d["status"] == "draft"


class TestSchedulingDomainService:
    def test_create_schedule(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule(
            tenant_id="t-001",
            project_id="p-001",
            name="Week 1 Schedule",
        )
        assert schedule.name == "Week 1 Schedule"
        assert len(schedule.domain_events) == 1

    def test_add_work_order(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")
        updated = service.add_work_order(
            schedule.id,
            work_order_id="wo-001",
            work_order_code="WO-001",
            priority=1,
            due_date="2026-07-01",
            operations=[
                {"operation_name": "CNC Milling", "workstation": "WS-01", "duration_hours": 4.0},
                {"operation_name": "Inspection", "workstation": "WS-02", "duration_hours": 1.0},
            ],
        )
        assert updated is not None
        assert len(updated.work_orders) == 1
        assert len(updated.work_orders[0].operations) == 2

    def test_add_resource(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")
        updated = service.add_resource(
            schedule.id,
            resource_id="WS-01",
            resource_name="CNC Machine 1",
            skills=["cnc_milling", "drilling"],
        )
        assert updated is not None
        assert len(updated.resources) == 1

    def test_add_constraint(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")
        updated = service.add_constraint(
            schedule.id,
            constraint_type=ConstraintType.CAPACITY,
            constraint_expression="WS-01: max 1 concurrent",
            priority=ConstraintPriority.HARD,
        )
        assert updated is not None
        assert len(updated.constraints) == 1

    def test_optimize_schedule(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test Schedule")

        service.add_resource(schedule.id, "WS-01", "CNC Machine 1")
        service.add_resource(schedule.id, "WS-02", "Inspection Station")

        service.add_work_order(
            schedule.id, "wo-001", "WO-001", priority=2,
            operations=[
                {"operation_name": "CNC Milling", "workstation": "WS-01", "duration_hours": 4.0},
                {"operation_name": "Inspection", "workstation": "WS-02", "duration_hours": 1.0},
            ],
        )
        service.add_work_order(
            schedule.id, "wo-002", "WO-002", priority=1,
            operations=[
                {"operation_name": "Drilling", "workstation": "WS-01", "duration_hours": 3.0},
                {"operation_name": "Quality Check", "workstation": "WS-02", "duration_hours": 1.0},
            ],
        )

        result = service.optimize_schedule(schedule.id)
        assert result is not None
        assert result.status == ScheduleStatus.OPTIMIZED
        assert result.makespan_hours > 0
        assert len(result.gantt_data) > 0
        assert len(result.resource_utilization) > 0

    def test_optimize_with_precedence(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")

        service.add_resource(schedule.id, "WS-01", "Machine 1")
        service.add_work_order(
            schedule.id, "wo-001", "WO-001",
            operations=[
                {"operation_name": "Step A", "workstation": "WS-01", "duration_hours": 2.0},
                {"operation_name": "Step B", "workstation": "WS-01", "duration_hours": 3.0,
                 "predecessor_ops": ["Step A"]},
            ],
        )

        result = service.optimize_schedule(schedule.id)
        assert result is not None
        step_b = next(g for g in result.gantt_data if g["operation_name"] == "Step B")
        step_a = next(g for g in result.gantt_data if g["operation_name"] == "Step A")
        assert step_b["start_time"] >= step_a["end_time"]

    def test_detect_conflicts(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")
        service.add_resource(schedule.id, "WS-01", "Machine 1")
        service.add_work_order(
            schedule.id, "wo-001", "WO-001",
            operations=[
                {"operation_name": "Op A", "workstation": "WS-01", "duration_hours": 8.0},
            ],
        )
        service.add_work_order(
            schedule.id, "wo-002", "WO-002",
            operations=[
                {"operation_name": "Op B", "workstation": "WS-01", "duration_hours": 8.0},
            ],
        )

        result = service.optimize_schedule(schedule.id)
        conflicts = service.detect_conflicts(schedule.id)
        assert result is not None
        assert isinstance(conflicts, list)

    def test_what_if_analysis(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")
        service.add_resource(schedule.id, "WS-01", "Machine 1")
        service.add_work_order(
            schedule.id, "wo-001", "WO-001",
            operations=[{"operation_name": "Op A", "workstation": "WS-01", "duration_hours": 4.0}],
        )
        service.optimize_schedule(schedule.id)

        result = service.what_if_analysis(schedule.id, {
            "add_work_orders": [{"work_order_id": "wo-003", "work_order_code": "WO-003", "priority": 1}],
        })
        assert result is not None
        assert "original" in result
        assert "simulated" in result

    def test_export_gantt_data(self) -> None:
        service = SchedulingDomainService()
        schedule = service.create_schedule("t-001", "p-001", "Test")
        service.add_resource(schedule.id, "WS-01", "Machine 1")
        service.add_work_order(
            schedule.id, "wo-001", "WO-001",
            operations=[{"operation_name": "Op A", "workstation": "WS-01", "duration_hours": 4.0}],
        )
        service.optimize_schedule(schedule.id)

        gantt = service.export_gantt_data(schedule.id)
        assert gantt is not None
        assert len(gantt) > 0

    def test_list_schedules(self) -> None:
        service = SchedulingDomainService()
        service.create_schedule("t-001", "p-001", "Schedule A")
        service.create_schedule("t-001", "p-002", "Schedule B")
        assert len(service.list_schedules()) == 2
        assert len(service.list_schedules(project_id="p-001")) == 1

    def test_get_schedule_not_found(self) -> None:
        service = SchedulingDomainService()
        assert service.get_schedule("nonexistent") is None