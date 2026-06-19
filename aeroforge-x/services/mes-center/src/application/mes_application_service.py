from __future__ import annotations

from typing import Any

from ..domain.entities.mes_entities import SerialNumber, Station, WorkOrder
from ..domain.services.mes_domain_service import ProgressTracker, SerialNumberDomainService, StationDomainService, WorkOrderDomainService
from ..infrastructure.mes_repository import SerialNumberRepository, StationRepository, WorkOrderRepository


class MesApplicationService:
    def __init__(
        self,
        wo_repo: WorkOrderRepository,
        station_repo: StationRepository,
        sn_repo: SerialNumberRepository,
    ) -> None:
        self._wo_repo = wo_repo
        self._station_repo = station_repo
        self._sn_repo = sn_repo
        self._wo_service = WorkOrderDomainService()
        self._station_service = StationDomainService()
        self._sn_service = SerialNumberDomainService()
        self._progress_tracker = ProgressTracker()

    async def create_work_order(self, product_model: str, quantity: int, priority: str, created_by: str) -> dict[str, Any]:
        order = self._wo_service.create_work_order(product_model, quantity, priority, route_id=None, created_by=created_by)
        await self._wo_repo.save(order.to_dict())
        return order.to_dict()

    async def list_work_orders(self, page: int = 1, page_size: int = 20, status: str | None = None) -> dict[str, Any]:
        offset = (page - 1) * page_size
        items = await self._wo_repo.find_all(offset=offset, limit=page_size, status=status)
        total = await self._wo_repo.count(status=status)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_work_order(self, order_id: str) -> dict[str, Any] | None:
        return await self._wo_repo.find_by_id(order_id)

    async def dispatch_work_order(self, order_id: str, station_id: str, material_available: bool = True) -> dict[str, Any] | None:
        order_data = await self._wo_repo.find_by_id(order_id)
        if order_data is None:
            return None
        order = self._reconstruct_work_order(order_data)
        station_data = await self._station_repo.find_by_id(station_id)
        if station_data is None:
            raise ValueError(f"Station '{station_id}' not found")
        station = Station(name=station_data["name"], equipment=station_data.get("equipment", ""), station_id=station_data["id"])
        station.status = station_data.get("status", "idle")
        self._wo_service.dispatch_work_order(order, station, material_available)
        await self._wo_repo.save(order.to_dict())
        return order.to_dict()

    async def update_work_order_status(self, order_id: str, action: str, progress: float | None = None) -> dict[str, Any] | None:
        order_data = await self._wo_repo.find_by_id(order_id)
        if order_data is None:
            return None
        order = self._reconstruct_work_order(order_data)
        if action == "start":
            order.start()
        elif action == "progress" and progress is not None:
            order.update_progress(progress)
        elif action == "complete":
            order.complete()
        await self._wo_repo.save(order.to_dict())
        return order.to_dict()

    async def list_stations(self) -> list[dict[str, Any]]:
        return await self._station_repo.find_all()

    async def get_station_status(self, station_id: str) -> dict[str, Any] | None:
        return await self._station_repo.find_by_id(station_id)

    async def assign_serial_number(self, item_code: str, batch_number: str | None, supplier: str | None) -> dict[str, Any]:
        sn = self._sn_service.assign_serial_number(item_code, batch_number, supplier)
        await self._sn_repo.save(sn.to_dict())
        return sn.to_dict()

    async def get_serial_number(self, serial_number: str) -> dict[str, Any] | None:
        return await self._sn_repo.find_by_sn(serial_number)

    async def link_serial_to_work_order(self, serial_number: str, work_order_id: str) -> dict[str, Any] | None:
        sn_data = await self._sn_repo.find_by_sn(serial_number)
        if sn_data is None:
            return None
        sn = SerialNumber(item_code=sn_data["item_code"], batch_number=sn_data.get("batch_number"), supplier=sn_data.get("supplier"))
        sn.serial_number = sn_data["serial_number"]
        sn.status = sn_data.get("status", "in_stock")
        self._sn_service.link_to_work_order(sn, work_order_id)
        await self._sn_repo.save(sn.to_dict())
        return sn.to_dict()

    def _reconstruct_work_order(self, data: dict[str, Any]) -> WorkOrder:
        order = WorkOrder(
            product_model=data["product_model"],
            quantity=data.get("quantity", 1),
            priority=data.get("priority", "normal"),
            route_id=data.get("route_id"),
            created_by=data.get("created_by", ""),
        )
        order.id = data["id"]
        order.order_code = data["order_code"]
        order.status = data["status"]
        order.station_id = data.get("station_id")
        order.progress_percent = data.get("progress_percent", 0.0)
        return order