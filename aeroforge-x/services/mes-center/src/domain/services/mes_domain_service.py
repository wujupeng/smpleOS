from __future__ import annotations

from typing import Any

from ..entities.mes_entities import SerialNumber, Station, WorkOrder


class WorkOrderDomainService:
    def create_work_order(self, product_model: str, quantity: int, priority: str, route_id: str | None, created_by: str) -> WorkOrder:
        return WorkOrder(product_model=product_model, quantity=quantity, priority=priority, route_id=route_id, created_by=created_by)

    def dispatch_work_order(self, order: WorkOrder, station: Station, material_available: bool = True) -> None:
        if not material_available:
            raise ValueError("Cannot dispatch: material has not passed IQC inspection")
        if station.status != Station.STATUS_IDLE:
            raise ValueError(f"Cannot dispatch: station '{station.name}' is not idle")
        order.dispatch(station_id=station.id)
        station.assign_task(order.order_code)

    def update_progress(self, order: WorkOrder, percent: float) -> None:
        order.update_progress(percent)

    def complete_work_order(self, order: WorkOrder, station: Station) -> None:
        order.complete()
        station.release()


class StationDomainService:
    def get_station_status(self, station: Station) -> dict[str, Any]:
        return station.to_dict()

    def schedule_task(self, station: Station, task_name: str) -> None:
        station.assign_task(task_name)

    def resolve_conflict(self, stations: list[Station], order: WorkOrder) -> Station | None:
        idle_stations = [s for s in stations if s.status == Station.STATUS_IDLE]
        if idle_stations:
            return idle_stations[0]
        sorted_stations = sorted(stations, key=lambda s: s.estimate_idle_time())
        return sorted_stations[0] if sorted_stations else None


class SerialNumberDomainService:
    def assign_serial_number(self, item_code: str, batch_number: str | None, supplier: str | None) -> SerialNumber:
        return SerialNumber(item_code=item_code, batch_number=batch_number, supplier=supplier)

    def link_to_work_order(self, sn: SerialNumber, work_order_id: str) -> None:
        sn.assign_to_work_order(work_order_id)

    def update_flight_hours(self, sn: SerialNumber, hours: float) -> None:
        sn.flight_hours += hours


class ProgressTracker:
    def calculate_progress(self, steps_total: int, steps_completed: int) -> float:
        if steps_total == 0:
            return 0.0
        return round((steps_completed / steps_total) * 100.0, 1)

    def estimate_completion(self, order: WorkOrder, steps_total: int, steps_completed: int, avg_step_duration_min: int = 30) -> dict[str, Any]:
        remaining = steps_total - steps_completed
        estimated_minutes = remaining * avg_step_duration_min
        return {
            "order_code": order.order_code,
            "progress_percent": self.calculate_progress(steps_total, steps_completed),
            "remaining_steps": remaining,
            "estimated_remaining_minutes": estimated_minutes,
        }