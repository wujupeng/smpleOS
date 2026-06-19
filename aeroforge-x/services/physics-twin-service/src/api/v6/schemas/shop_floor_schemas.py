"""AeroForge-X V6.0 Digital Factory Pydantic V2 Schemas
REQ-ENG-009, REQ-FACTORY-001~022
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


class RegisterEquipmentRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_id: str = Field(min_length=1)
    equipment_name: str = Field(min_length=1)
    equipment_type: str = Field(pattern="^(PLC|CNC|Robot|AGV|IoTSensor)$")
    protocol: str = Field(pattern="^(OPC-UA|MQTT)$")
    sampling_rate_ms: int = Field(default=1000, gt=0)
    location: str = ""


class OPCUAConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_id: str = Field(min_length=1)
    server_url: str = Field(min_length=1)
    node_ids: list[str] = Field(default_factory=list)
    security_mode: str = "None"


class MQTTConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_id: str = Field(min_length=1)
    broker_host: str = Field(min_length=1)
    broker_port: int = Field(default=1883, gt=0)
    topic: str = ""
    qos: int = Field(default=1, ge=0, le=2)


class CollectionStatusResponse(BaseModel):
    equipment_id: str
    status: str
    protocol: str
    sampling_rate_ms: int


class DataPointRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    timestamp: float
    equipment_id: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    value: float
    unit: str = ""


class DataQualityResponse(BaseModel):
    is_valid: bool
    validation_failures: list[str] = Field(default_factory=list)
    last_known_good_value: float | None = None


class SamplingRateConfigRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_type: str = Field(pattern="^(PLC|CNC|Robot|AGV|IoTSensor)$")
    rate_ms: int = Field(gt=0)


class OEEComputeRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_id: str = Field(min_length=1)
    planned_time: float = Field(gt=0)
    run_time: float = Field(ge=0)
    ideal_cycle_time: float = Field(gt=0)
    actual_cycle_time: float = Field(gt=0)
    total_pieces: float = Field(ge=0)
    good_pieces: float = Field(ge=0)


class OEEResponse(BaseModel):
    equipment_id: str
    availability: float = 0.0
    performance: float = 0.0
    quality: float = 0.0
    oee: float = 0.0


class AGVStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    agv_id: str = Field(min_length=1)
    location: str = ""
    task_status: str = "Idle"
    battery_level: float = Field(default=100.0, ge=0, le=100)
    collision_avoidance_status: str = "Clear"


class AGVFleetStatusResponse(BaseModel):
    total_agvs: int
    active_agvs: int
    idle_agvs: int
    low_battery_agvs: int
    details: list[dict] = Field(default_factory=list)


class BottleneckResponse(BaseModel):
    constraint_operation_id: str
    utilization_rate: float
    suggested_capacity_adjustment: str


class DeliveryImpactResponse(BaseModel):
    bottleneck: dict
    delivery_delay_days: float
    mitigation_recommendation: str


class ShopFloorEventResponse(BaseModel):
    event_id: str
    event_type: str
    source_equipment_id: str
    payload: dict = Field(default_factory=dict)
    emitted_at: float


class DeviationAlertRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    equipment_id: str = Field(min_length=1)
    twin_predicted_value: float
    physical_actual_value: float


class TwinCommandRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    command_type: str = Field(min_length=1)
    parameters: dict = Field(default_factory=dict)
    authorized_by_production: str = ""
    authorized_by_safety: str = ""