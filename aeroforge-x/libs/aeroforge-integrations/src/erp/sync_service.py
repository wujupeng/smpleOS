from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .adapter import (
    ERPAdapter,
    ERPBOMItem,
    ERPConnectionConfig,
    ERPCostData,
    ERPInventoryData,
    ERPType,
    ERPWorkOrder,
    MaterialMaster,
    SyncDirection,
    SyncRecord,
    SyncStatus,
    create_erp_adapter,
)

logger = logging.getLogger(__name__)


class ERPDataSyncService:
    def __init__(self, config: ERPConnectionConfig) -> None:
        self._adapter = create_erp_adapter(config)
        self._sync_history: list[SyncRecord] = []
        self._connected = False

    def connect(self) -> dict[str, Any]:
        try:
            self._connected = self._adapter.connect()
            return {"connected": self._connected, "erp_type": self._adapter.config.erp_type.value}
        except Exception as e:
            logger.error("Failed to connect to ERP: %s", e)
            return {"connected": False, "error": str(e)}

    def disconnect(self) -> None:
        self._adapter.disconnect()
        self._connected = False

    def test_connection(self) -> dict[str, Any]:
        return self._adapter.test_connection()

    def sync_material_master(self, material_code: str | None = None) -> SyncRecord:
        sync_id = f"SYNC-MAT-{secrets.token_hex(4)}"
        record = SyncRecord(
            sync_id=sync_id,
            data_type="material_master",
            direction=SyncDirection.ERP_TO_AEROFORGE,
            status=SyncStatus.IN_PROGRESS,
        )

        try:
            materials = self._adapter.get_material_master(material_code)
            record.records_total = len(materials)
            record.records_success = len(materials)
            record.status = SyncStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            record.details = {"materials": [m.to_dict() for m in materials]}

            logger.info("Material master sync completed: %d records", len(materials))
        except Exception as e:
            record.status = SyncStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now(timezone.utc)
            logger.error("Material master sync failed: %s", e)

        self._sync_history.append(record)
        return record

    def sync_bom_to_erp(self, bom_items: list[dict[str, Any]]) -> SyncRecord:
        sync_id = f"SYNC-BOM-{secrets.token_hex(4)}"
        record = SyncRecord(
            sync_id=sync_id,
            data_type="bom",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.IN_PROGRESS,
        )

        try:
            items = [
                ERPBOMItem(
                    parent_part=item.get("parent_part", ""),
                    child_part=item.get("child_part", ""),
                    quantity=item.get("quantity", 1),
                    unit=item.get("unit", "EA"),
                    bom_level=item.get("bom_level", 1),
                )
                for item in bom_items
            ]
            result = self._adapter.push_bom(items)
            record.records_total = result.records_total
            record.records_success = result.records_success
            record.status = SyncStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)

            logger.info("BOM sync to ERP completed: %d items", len(items))
        except Exception as e:
            record.status = SyncStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now(timezone.utc)
            logger.error("BOM sync to ERP failed: %s", e)

        self._sync_history.append(record)
        return record

    def sync_work_order_to_erp(self, work_orders: list[dict[str, Any]]) -> SyncRecord:
        sync_id = f"SYNC-WO-{secrets.token_hex(4)}"
        record = SyncRecord(
            sync_id=sync_id,
            data_type="work_order",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.IN_PROGRESS,
        )

        try:
            orders = [
                ERPWorkOrder(
                    order_number=wo.get("order_number", ""),
                    material_code=wo.get("material_code", ""),
                    quantity=wo.get("quantity", 0),
                    planned_start=wo.get("planned_start", ""),
                    planned_end=wo.get("planned_end", ""),
                    status=wo.get("status", "created"),
                )
                for wo in work_orders
            ]
            result = self._adapter.push_work_order(orders)
            record.records_total = result.records_total
            record.records_success = result.records_success
            record.status = SyncStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)

            logger.info("Work order sync to ERP completed: %d orders", len(orders))
        except Exception as e:
            record.status = SyncStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now(timezone.utc)
            logger.error("Work order sync to ERP failed: %s", e)

        self._sync_history.append(record)
        return record

    def sync_cost_from_erp(self, material_code: str | None = None) -> SyncRecord:
        sync_id = f"SYNC-COST-{secrets.token_hex(4)}"
        record = SyncRecord(
            sync_id=sync_id,
            data_type="cost",
            direction=SyncDirection.ERP_TO_AEROFORGE,
            status=SyncStatus.IN_PROGRESS,
        )

        try:
            costs = self._adapter.get_cost_data(material_code)
            record.records_total = len(costs)
            record.records_success = len(costs)
            record.status = SyncStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            record.details = {"costs": [c.to_dict() for c in costs]}

            logger.info("Cost data sync completed: %d records", len(costs))
        except Exception as e:
            record.status = SyncStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now(timezone.utc)
            logger.error("Cost data sync failed: %s", e)

        self._sync_history.append(record)
        return record

    def sync_inventory_from_erp(self, material_code: str | None = None) -> SyncRecord:
        sync_id = f"SYNC-INV-{secrets.token_hex(4)}"
        record = SyncRecord(
            sync_id=sync_id,
            data_type="inventory",
            direction=SyncDirection.ERP_TO_AEROFORGE,
            status=SyncStatus.IN_PROGRESS,
        )

        try:
            inventory = self._adapter.get_inventory(material_code)
            record.records_total = len(inventory)
            record.records_success = len(inventory)
            record.status = SyncStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            record.details = {"inventory": [i.to_dict() for i in inventory]}

            logger.info("Inventory sync completed: %d records", len(inventory))
        except Exception as e:
            record.status = SyncStatus.FAILED
            record.error_message = str(e)
            record.completed_at = datetime.now(timezone.utc)
            logger.error("Inventory sync failed: %s", e)

        self._sync_history.append(record)
        return record

    def get_sync_history(self, data_type: str | None = None, limit: int = 50) -> list[SyncRecord]:
        records = self._sync_history
        if data_type:
            records = [r for r in records if r.data_type == data_type]
        return sorted(records, key=lambda r: r.started_at, reverse=True)[:limit]

    def get_sync_status(self) -> dict[str, Any]:
        recent = self._sync_history[-10:] if self._sync_history else []
        return {
            "connected": self._connected,
            "erp_type": self._adapter.config.erp_type.value,
            "total_syncs": len(self._sync_history),
            "recent_syncs": [r.to_dict() for r in recent],
        }

    def get_config(self) -> dict[str, Any]:
        return self._adapter.config.to_dict()