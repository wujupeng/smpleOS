from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    ERP_TO_AEROFORGE = "erp_to_aeroforge"
    AEROFORGE_TO_ERP = "aeroforge_to_erp"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ERPType(str, Enum):
    SAP = "sap"
    ORACLE = "oracle"
    GENERIC = "generic"


@dataclass
class ERPConnectionConfig:
    erp_type: ERPType
    base_url: str
    username: str = ""
    password: str = ""
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    timeout_seconds: int = 30
    retry_count: int = 3
    verify_ssl: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "erp_type": self.erp_type.value,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "verify_ssl": self.verify_ssl,
        }


@dataclass
class SyncRecord:
    sync_id: str
    data_type: str
    direction: SyncDirection
    status: SyncStatus
    records_total: int = 0
    records_success: int = 0
    records_failed: int = 0
    error_message: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id,
            "data_type": self.data_type,
            "direction": self.direction.value,
            "status": self.status.value,
            "records_total": self.records_total,
            "records_success": self.records_success,
            "records_failed": self.records_failed,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class MaterialMaster:
    material_code: str
    name: str
    category: str
    unit: str
    specification: str = ""
    weight_kg: float = 0
    price: float = 0
    currency: str = "CNY"
    supplier_code: str = ""
    lead_time_days: int = 0
    safety_stock: float = 0
    erp_source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_code": self.material_code,
            "name": self.name,
            "category": self.category,
            "unit": self.unit,
            "specification": self.specification,
            "weight_kg": self.weight_kg,
            "price": self.price,
            "currency": self.currency,
            "supplier_code": self.supplier_code,
            "lead_time_days": self.lead_time_days,
            "safety_stock": self.safety_stock,
            "erp_source": self.erp_source,
        }


@dataclass
class ERPBOMItem:
    parent_part: str
    child_part: str
    quantity: float = 1
    unit: str = "EA"
    bom_level: int = 1
    alternative_group: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_part": self.parent_part,
            "child_part": self.child_part,
            "quantity": self.quantity,
            "unit": self.unit,
            "bom_level": self.bom_level,
            "alternative_group": self.alternative_group,
        }


@dataclass
class ERPWorkOrder:
    order_number: str
    material_code: str
    quantity: float
    planned_start: str = ""
    planned_end: str = ""
    status: str = "created"
    cost_center: str = ""
    routing_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_number": self.order_number,
            "material_code": self.material_code,
            "quantity": self.quantity,
            "planned_start": self.planned_start,
            "planned_end": self.planned_end,
            "status": self.status,
            "cost_center": self.cost_center,
            "routing_id": self.routing_id,
        }


@dataclass
class ERPCostData:
    material_code: str
    standard_cost: float
    actual_cost: float = 0
    currency: str = "CNY"
    cost_element: str = ""
    period: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_code": self.material_code,
            "standard_cost": self.standard_cost,
            "actual_cost": self.actual_cost,
            "currency": self.currency,
            "cost_element": self.cost_element,
            "period": self.period,
        }


@dataclass
class ERPInventoryData:
    material_code: str
    plant: str
    storage_location: str = ""
    available_quantity: float = 0
    reserved_quantity: float = 0
    unit: str = "EA"

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_code": self.material_code,
            "plant": self.plant,
            "storage_location": self.storage_location,
            "available_quantity": self.available_quantity,
            "reserved_quantity": self.reserved_quantity,
            "unit": self.unit,
        }


class ERPAdapter(ABC):
    def __init__(self, config: ERPConnectionConfig) -> None:
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_material_master(self, material_code: str | None = None) -> list[MaterialMaster]:
        ...

    @abstractmethod
    def push_bom(self, bom_items: list[ERPBOMItem]) -> SyncRecord:
        ...

    @abstractmethod
    def push_work_order(self, work_orders: list[ERPWorkOrder]) -> SyncRecord:
        ...

    @abstractmethod
    def get_cost_data(self, material_code: str | None = None) -> list[ERPCostData]:
        ...

    @abstractmethod
    def get_inventory(self, material_code: str | None = None) -> list[ERPInventoryData]:
        ...


class SAPAdapter(ERPAdapter):
    def connect(self) -> bool:
        logger.info("Connecting to SAP ERP: %s", self.config.base_url)
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from SAP ERP")

    def test_connection(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "erp_type": "SAP",
            "base_url": self.config.base_url,
        }

    def get_material_master(self, material_code: str | None = None) -> list[MaterialMaster]:
        if not self._connected:
            raise ConnectionError("Not connected to SAP")
        logger.info("Fetching material master from SAP: code=%s", material_code)
        return [
            MaterialMaster(
                material_code="MAT-001",
                name="Aluminum Alloy 7075-T6",
                category="Raw Material",
                unit="KG",
                specification="AMS 4044",
                weight_kg=1.0,
                price=85.0,
                supplier_code="SUP-001",
                lead_time_days=14,
                safety_stock=100,
                erp_source="SAP",
            ),
        ]

    def push_bom(self, bom_items: list[ERPBOMItem]) -> SyncRecord:
        if not self._connected:
            raise ConnectionError("Not connected to SAP")
        logger.info("Pushing BOM to SAP: %d items", len(bom_items))
        return SyncRecord(
            sync_id="SAP-BOM-001",
            data_type="bom",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.COMPLETED,
            records_total=len(bom_items),
            records_success=len(bom_items),
        )

    def push_work_order(self, work_orders: list[ERPWorkOrder]) -> SyncRecord:
        if not self._connected:
            raise ConnectionError("Not connected to SAP")
        logger.info("Pushing work orders to SAP: %d orders", len(work_orders))
        return SyncRecord(
            sync_id="SAP-WO-001",
            data_type="work_order",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.COMPLETED,
            records_total=len(work_orders),
            records_success=len(work_orders),
        )

    def get_cost_data(self, material_code: str | None = None) -> list[ERPCostData]:
        if not self._connected:
            raise ConnectionError("Not connected to SAP")
        return [
            ERPCostData(
                material_code=material_code or "MAT-001",
                standard_cost=85.0,
                actual_cost=82.5,
                currency="CNY",
                cost_element="Raw Material",
                period="2026-06",
            ),
        ]

    def get_inventory(self, material_code: str | None = None) -> list[ERPInventoryData]:
        if not self._connected:
            raise ConnectionError("Not connected to SAP")
        return [
            ERPInventoryData(
                material_code=material_code or "MAT-001",
                plant="P100",
                storage_location="WH01",
                available_quantity=500,
                reserved_quantity=100,
            ),
        ]


class OracleERPAdapter(ERPAdapter):
    def connect(self) -> bool:
        logger.info("Connecting to Oracle ERP: %s", self.config.base_url)
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def test_connection(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "erp_type": "Oracle",
            "base_url": self.config.base_url,
        }

    def get_material_master(self, material_code: str | None = None) -> list[MaterialMaster]:
        if not self._connected:
            raise ConnectionError("Not connected to Oracle ERP")
        return [
            MaterialMaster(
                material_code="MAT-002",
                name="Titanium Alloy Ti-6Al-4V",
                category="Raw Material",
                unit="KG",
                specification="AMS 4928",
                weight_kg=1.0,
                price=350.0,
                supplier_code="SUP-002",
                lead_time_days=28,
                safety_stock=50,
                erp_source="Oracle",
            ),
        ]

    def push_bom(self, bom_items: list[ERPBOMItem]) -> SyncRecord:
        if not self._connected:
            raise ConnectionError("Not connected to Oracle ERP")
        return SyncRecord(
            sync_id="ORA-BOM-001",
            data_type="bom",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.COMPLETED,
            records_total=len(bom_items),
            records_success=len(bom_items),
        )

    def push_work_order(self, work_orders: list[ERPWorkOrder]) -> SyncRecord:
        if not self._connected:
            raise ConnectionError("Not connected to Oracle ERP")
        return SyncRecord(
            sync_id="ORA-WO-001",
            data_type="work_order",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.COMPLETED,
            records_total=len(work_orders),
            records_success=len(work_orders),
        )

    def get_cost_data(self, material_code: str | None = None) -> list[ERPCostData]:
        if not self._connected:
            raise ConnectionError("Not connected to Oracle ERP")
        return [
            ERPCostData(
                material_code=material_code or "MAT-002",
                standard_cost=350.0,
                actual_cost=345.0,
                currency="CNY",
                cost_element="Raw Material",
                period="2026-06",
            ),
        ]

    def get_inventory(self, material_code: str | None = None) -> list[ERPInventoryData]:
        if not self._connected:
            raise ConnectionError("Not connected to Oracle ERP")
        return [
            ERPInventoryData(
                material_code=material_code or "MAT-002",
                plant="P200",
                storage_location="WH02",
                available_quantity=200,
                reserved_quantity=30,
            ),
        ]


class GenericERPAdapter(ERPAdapter):
    def connect(self) -> bool:
        logger.info("Connecting to Generic ERP: %s", self.config.base_url)
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def test_connection(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "erp_type": "Generic",
            "base_url": self.config.base_url,
        }

    def get_material_master(self, material_code: str | None = None) -> list[MaterialMaster]:
        if not self._connected:
            raise ConnectionError("Not connected to ERP")
        return [
            MaterialMaster(
                material_code=material_code or "MAT-GEN-001",
                name="Generic Material",
                category="Raw Material",
                unit="KG",
                erp_source="Generic",
            ),
        ]

    def push_bom(self, bom_items: list[ERPBOMItem]) -> SyncRecord:
        if not self._connected:
            raise ConnectionError("Not connected to ERP")
        return SyncRecord(
            sync_id="GEN-BOM-001",
            data_type="bom",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.COMPLETED,
            records_total=len(bom_items),
            records_success=len(bom_items),
        )

    def push_work_order(self, work_orders: list[ERPWorkOrder]) -> SyncRecord:
        if not self._connected:
            raise ConnectionError("Not connected to ERP")
        return SyncRecord(
            sync_id="GEN-WO-001",
            data_type="work_order",
            direction=SyncDirection.AEROFORGE_TO_ERP,
            status=SyncStatus.COMPLETED,
            records_total=len(work_orders),
            records_success=len(work_orders),
        )

    def get_cost_data(self, material_code: str | None = None) -> list[ERPCostData]:
        if not self._connected:
            raise ConnectionError("Not connected to ERP")
        return []

    def get_inventory(self, material_code: str | None = None) -> list[ERPInventoryData]:
        if not self._connected:
            raise ConnectionError("Not connected to ERP")
        return []


def create_erp_adapter(config: ERPConnectionConfig) -> ERPAdapter:
    adapters = {
        ERPType.SAP: SAPAdapter,
        ERPType.ORACLE: OracleERPAdapter,
        ERPType.GENERIC: GenericERPAdapter,
    }
    adapter_class = adapters.get(config.erp_type)
    if adapter_class is None:
        raise ValueError(f"Unsupported ERP type: {config.erp_type}")
    return adapter_class(config)