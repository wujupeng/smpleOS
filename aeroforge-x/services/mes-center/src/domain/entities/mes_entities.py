from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import AggregateRoot, DomainEvent
from aeroforge_common.utils.helpers import generate_code


class WorkOrder(AggregateRoot):
    STATUS_CREATED = "created"
    STATUS_DISPATCHED = "dispatched"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CLOSED = "closed"

    VALID_TRANSITIONS = {
        STATUS_CREATED: {STATUS_DISPATCHED},
        STATUS_DISPATCHED: {STATUS_IN_PROGRESS},
        STATUS_IN_PROGRESS: {STATUS_COMPLETED},
        STATUS_COMPLETED: {STATUS_CLOSED},
    }

    def __init__(
        self,
        product_model: str,
        quantity: int = 1,
        priority: str = "normal",
        route_id: str | None = None,
        created_by: str = "",
    ) -> None:
        super().__init__()
        self.order_code: str = generate_code("AAF-WO")
        self.product_model = product_model
        self.quantity = quantity
        self.priority = priority
        self.status: str = self.STATUS_CREATED
        self.route_id = route_id
        self.station_id: str | None = None
        self.planned_start_date: datetime | None = None
        self.planned_end_date: datetime | None = None
        self.actual_start_date: datetime | None = None
        self.actual_end_date: datetime | None = None
        self.created_by = created_by
        self.progress_percent: float = 0.0
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    def dispatch(self, station_id: str) -> None:
        if self.status not in self.VALID_TRANSITIONS.get(self.STATUS_CREATED, set()):
            if self.status != self.STATUS_CREATED:
                raise ValueError(f"Cannot dispatch work order in status '{self.status}'")
        self.station_id = station_id
        self.status = self.STATUS_DISPATCHED
        self.updated_at = datetime.now(timezone.utc)
        event = DomainEvent(
            event_type="workorder.created",
            aggregate_id=self.id,
            payload={"order_code": self.order_code, "station_id": station_id},
        )
        self.add_domain_event(event)

    def start(self) -> None:
        if self.status != self.STATUS_DISPATCHED:
            raise ValueError(f"Cannot start work order in status '{self.status}'")
        self.status = self.STATUS_IN_PROGRESS
        self.actual_start_date = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def update_progress(self, percent: float) -> None:
        if self.status != self.STATUS_IN_PROGRESS:
            raise ValueError("Can only update progress for in-progress orders")
        self.progress_percent = min(100.0, max(0.0, percent))
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        if self.status != self.STATUS_IN_PROGRESS:
            raise ValueError(f"Cannot complete work order in status '{self.status}'")
        self.status = self.STATUS_COMPLETED
        self.progress_percent = 100.0
        self.actual_end_date = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "order_code": self.order_code,
            "product_model": self.product_model,
            "quantity": self.quantity,
            "priority": self.priority,
            "status": self.status,
            "route_id": self.route_id,
            "station_id": self.station_id,
            "planned_start_date": self.planned_start_date.isoformat() if self.planned_start_date else None,
            "planned_end_date": self.planned_end_date.isoformat() if self.planned_end_date else None,
            "actual_start_date": self.actual_start_date.isoformat() if self.actual_start_date else None,
            "actual_end_date": self.actual_end_date.isoformat() if self.actual_end_date else None,
            "progress_percent": self.progress_percent,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Station:
    STATUS_IDLE = "idle"
    STATUS_BUSY = "busy"
    STATUS_MAINTENANCE = "maintenance"

    def __init__(self, name: str, equipment: str = "", station_id: str | None = None) -> None:
        self.id = station_id or generate_code("STN")
        self.name = name
        self.equipment = equipment
        self.status: str = self.STATUS_IDLE
        self.current_task: str | None = None
        self.operators: list[str] = []
        self.created_at: datetime = datetime.now(timezone.utc)

    def assign_task(self, task_name: str) -> None:
        if self.status != self.STATUS_IDLE:
            raise ValueError(f"Station '{self.name}' is not idle (status: {self.status})")
        self.status = self.STATUS_BUSY
        self.current_task = task_name

    def release(self) -> None:
        self.status = self.STATUS_IDLE
        self.current_task = None

    def estimate_idle_time(self) -> int:
        if self.status == self.STATUS_IDLE:
            return 0
        return 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "equipment": self.equipment,
            "status": self.status,
            "current_task": self.current_task,
            "operators": self.operators,
            "estimated_idle_minutes": self.estimate_idle_time(),
            "created_at": self.created_at.isoformat(),
        }


class SerialNumber:
    STATUS_IN_STOCK = "in_stock"
    STATUS_IN_PRODUCTION = "in_production"
    STATUS_INSTALLED = "installed"
    STATUS_RETIRED = "retired"

    def __init__(
        self,
        item_code: str,
        batch_number: str | None = None,
        supplier: str | None = None,
    ) -> None:
        self.serial_number: str = generate_code("SN")
        self.item_code = item_code
        self.batch_number = batch_number
        self.supplier = supplier
        self.work_order_id: str | None = None
        self.manufacturing_date: datetime | None = None
        self.installation_date: datetime | None = None
        self.installer: str | None = None
        self.flight_hours: float = 0.0
        self.status: str = self.STATUS_IN_STOCK
        self.created_at: datetime = datetime.now(timezone.utc)

    def assign_to_work_order(self, work_order_id: str) -> None:
        if self.status != self.STATUS_IN_STOCK:
            raise ValueError(f"Cannot assign serial number in status '{self.status}'")
        self.work_order_id = work_order_id
        self.status = self.STATUS_IN_PRODUCTION
        self.manufacturing_date = datetime.now(timezone.utc)

    def install(self, installer: str) -> None:
        if self.status != self.STATUS_IN_PRODUCTION:
            raise ValueError(f"Cannot install serial number in status '{self.status}'")
        self.status = self.STATUS_INSTALLED
        self.installer = installer
        self.installation_date = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "serial_number": self.serial_number,
            "item_code": self.item_code,
            "batch_number": self.batch_number,
            "supplier": self.supplier,
            "work_order_id": self.work_order_id,
            "manufacturing_date": self.manufacturing_date.isoformat() if self.manufacturing_date else None,
            "installation_date": self.installation_date.isoformat() if self.installation_date else None,
            "installer": self.installer,
            "flight_hours": self.flight_hours,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }