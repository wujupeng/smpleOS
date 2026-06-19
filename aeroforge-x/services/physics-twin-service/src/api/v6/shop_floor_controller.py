from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.digital_factory.shop_floor_data_collector_service import (
    ShopFloorDataCollectorService,
    EquipmentRegistration,
    EquipmentType,
    Protocol,
    OPCUAConfig,
    MQTTConfig,
)

router = APIRouter(prefix="/api/v6/physics-twin", tags=["Shop Floor v6"])

_collector_service = ShopFloorDataCollectorService()


@router.post("/shop-floor/equipment")
async def register_equipment(body: dict[str, Any]):
    equipment = EquipmentRegistration(
        equipment_id=body.get("equipment_id", ""),
        equipment_name=body.get("equipment_name", ""),
        equipment_type=EquipmentType(body.get("equipment_type", "PLC")),
        protocol=Protocol(body.get("protocol", "OPC-UA")),
        sampling_rate_ms=body.get("sampling_rate_ms", 1000),
        location=body.get("location", ""),
    )
    try:
        eq_id = _collector_service.registerEquipment(equipment=equipment)
        return {"equipment_id": eq_id, "status": "Registered"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shop-floor/equipment/{equipment_id}/start-opcua")
async def start_opcua_collection(equipment_id: str, body: dict[str, Any]):
    config = OPCUAConfig(
        server_url=body.get("server_url", "opc.tcp://localhost:4840"),
        node_ids=body.get("node_ids", []),
        security_mode=body.get("security_mode", "None"),
    )
    try:
        result = _collector_service.startOPCUACollection(equipment_id=equipment_id, config=config)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/shop-floor/equipment/{equipment_id}/start-mqtt")
async def start_mqtt_collection(equipment_id: str, body: dict[str, Any]):
    config = MQTTConfig(
        broker_host=body.get("broker_host", "localhost"),
        broker_port=body.get("broker_port", 1883),
        topic=body.get("topic", "aeroforge/factory/#"),
        qos=body.get("qos", 1),
    )
    try:
        result = _collector_service.startMQTTCollection(equipment_id=equipment_id, config=config)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))