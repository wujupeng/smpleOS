import pytest

from services.mes_center.src.domain.entities.mes_entities import SerialNumber, Station, WorkOrder
from services.mes_center.src.domain.services.mes_domain_service import (
    ProgressTracker, SerialNumberDomainService, StationDomainService, WorkOrderDomainService,
)


class TestWorkOrder:
    def test_create_work_order(self) -> None:
        order = WorkOrder(product_model="AAF-001", quantity=2, priority="normal", created_by="user-1")
        assert order.order_code.startswith("AAF-WO-")
        assert order.status == "created"

    def test_dispatch_work_order(self) -> None:
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        station = Station(name="碳纤维铺层工位", equipment="自动铺层机")
        order.dispatch(station_id=station.id)
        assert order.status == "dispatched"
        assert len(order.domain_events) == 1

    def test_start_work_order(self) -> None:
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        order.dispatch(station_id="stn-1")
        order.start()
        assert order.status == "in_progress"
        assert order.actual_start_date is not None

    def test_complete_work_order(self) -> None:
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        order.dispatch(station_id="stn-1")
        order.start()
        order.complete()
        assert order.status == "completed"
        assert order.progress_percent == 100.0

    def test_cannot_dispatch_non_created(self) -> None:
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        order.dispatch(station_id="stn-1")
        with pytest.raises(ValueError, match="Cannot dispatch"):
            order.dispatch(station_id="stn-2")

    def test_update_progress(self) -> None:
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        order.dispatch(station_id="stn-1")
        order.start()
        order.update_progress(50.0)
        assert order.progress_percent == 50.0


class TestStation:
    def test_assign_task(self) -> None:
        station = Station(name="Test Station")
        station.assign_task("WO-001")
        assert station.status == "busy"
        assert station.current_task == "WO-001"

    def test_cannot_assign_to_busy_station(self) -> None:
        station = Station(name="Test Station")
        station.assign_task("WO-001")
        with pytest.raises(ValueError, match="not idle"):
            station.assign_task("WO-002")

    def test_release_station(self) -> None:
        station = Station(name="Test Station")
        station.assign_task("WO-001")
        station.release()
        assert station.status == "idle"
        assert station.current_task is None


class TestSerialNumber:
    def test_create_serial_number(self) -> None:
        sn = SerialNumber(item_code="AAF-SPAR-001", batch_number="B2026-001", supplier="CF-Tech")
        assert sn.serial_number.startswith("SN-")
        assert sn.status == "in_stock"

    def test_assign_to_work_order(self) -> None:
        sn = SerialNumber(item_code="AAF-SPAR-001")
        sn.assign_to_work_order("wo-1")
        assert sn.status == "in_production"
        assert sn.work_order_id == "wo-1"

    def test_install(self) -> None:
        sn = SerialNumber(item_code="AAF-SPAR-001")
        sn.assign_to_work_order("wo-1")
        sn.install(installer="张工")
        assert sn.status == "installed"
        assert sn.installer == "张工"

    def test_cannot_assign_installed_sn(self) -> None:
        sn = SerialNumber(item_code="AAF-SPAR-001")
        sn.assign_to_work_order("wo-1")
        sn.install(installer="张工")
        with pytest.raises(ValueError, match="Cannot assign"):
            sn.assign_to_work_order("wo-2")


class TestWorkOrderDomainService:
    def test_dispatch_with_material_check(self) -> None:
        service = WorkOrderDomainService()
        order = service.create_work_order("AAF-001", 1, "normal", None, "user-1")
        station = Station(name="Test Station")
        service.dispatch_work_order(order, station, material_available=True)
        assert order.status == "dispatched"

    def test_dispatch_blocked_by_iqc(self) -> None:
        service = WorkOrderDomainService()
        order = service.create_work_order("AAF-001", 1, "normal", None, "user-1")
        station = Station(name="Test Station")
        with pytest.raises(ValueError, match="IQC"):
            service.dispatch_work_order(order, station, material_available=False)


class TestProgressTracker:
    def test_calculate_progress(self) -> None:
        tracker = ProgressTracker()
        assert tracker.calculate_progress(10, 5) == 50.0
        assert tracker.calculate_progress(0, 0) == 0.0

    def test_estimate_completion(self) -> None:
        tracker = ProgressTracker()
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        result = tracker.estimate_completion(order, steps_total=10, steps_completed=3, avg_step_duration_min=30)
        assert result["progress_percent"] == 30.0
        assert result["remaining_steps"] == 7
        assert result["estimated_remaining_minutes"] == 210


class TestStationDomainService:
    def test_resolve_conflict_picks_idle(self) -> None:
        service = StationDomainService()
        s1 = Station(name="Busy Station")
        s1.assign_task("WO-001")
        s2 = Station(name="Idle Station")
        order = WorkOrder(product_model="AAF-001", created_by="user-1")
        result = service.resolve_conflict([s1, s2], order)
        assert result == s2