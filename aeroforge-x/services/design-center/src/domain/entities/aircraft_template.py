from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class LayoutType(str, Enum):
    CONVENTIONAL = "conventional"
    CANARD = "canard"
    FLYING_WING = "flying_wing"
    MULTI_ROTOR = "multi_rotor"
    TILT_ROTOR = "tilt_rotor"
    THRUST_VECTOR = "thrust_vector"
    STANDARD_CLASS = "standard_class"
    OPEN_CLASS = "open_class"
    VTOL_FIXED_WING = "vtol_fixed_wing"


@dataclass
class AircraftTemplate:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    aircraft_type: str = "fixed_wing"
    layout_type: str = "conventional"
    description: str = ""
    default_spec: dict[str, Any] = field(default_factory=dict)
    design_rule_set: str = "default"
    material_scope: list[str] = field(default_factory=list)
    certification_standards: list[str] = field(default_factory=list)
    default_settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aircraft_type": self.aircraft_type,
            "layout_type": self.layout_type,
            "description": self.description,
            "default_spec": self.default_spec,
            "design_rule_set": self.design_rule_set,
            "material_scope": self.material_scope,
            "certification_standards": self.certification_standards,
            "default_settings": self.default_settings,
        }


BUILTIN_TEMPLATES: list[AircraftTemplate] = [
    AircraftTemplate(
        name="固定翼 - 常规布局",
        aircraft_type="fixed_wing",
        layout_type="conventional",
        description="传统尾翼布局固定翼飞行器，适用于通用航空和教练机",
        default_spec={
            "payload_kg": 120, "range_km": 200, "cruise_speed_kmh": 120,
            "takeoff_distance_m": 80, "power_type": "electric",
        },
        design_rule_set="fixed_wing_conventional",
        material_scope=["aluminum", "carbon_fiber", "steel", "titanium"],
        certification_standards=["CCAR-23"],
        default_settings={"design_margin": 1.5, "max_operating_speed_kmh": 300},
    ),
    AircraftTemplate(
        name="固定翼 - 鸭式布局",
        aircraft_type="fixed_wing",
        layout_type="canard",
        description="鸭翼布局固定翼，高机动性设计",
        default_spec={
            "payload_kg": 100, "range_km": 300, "cruise_speed_kmh": 180,
            "takeoff_distance_m": 100, "power_type": "electric",
        },
        design_rule_set="fixed_wing_canard",
        material_scope=["carbon_fiber", "titanium", "aluminum"],
        certification_standards=["CCAR-23"],
        default_settings={"design_margin": 1.5, "max_operating_speed_kmh": 350},
    ),
    AircraftTemplate(
        name="固定翼 - 飞翼布局",
        aircraft_type="fixed_wing",
        layout_type="flying_wing",
        description="飞翼布局，低阻力高隐身设计",
        default_spec={
            "payload_kg": 80, "range_km": 500, "cruise_speed_kmh": 200,
            "takeoff_distance_m": 150, "power_type": "electric",
        },
        design_rule_set="fixed_wing_flying_wing",
        material_scope=["carbon_fiber", "composite"],
        certification_standards=["CCAR-23"],
        default_settings={"design_margin": 2.0, "max_operating_speed_kmh": 400},
    ),
    AircraftTemplate(
        name="eVTOL - 多旋翼",
        aircraft_type="evtol",
        layout_type="multi_rotor",
        description="多旋翼电动垂直起降飞行器，城市空中出行",
        default_spec={
            "payload_kg": 200, "range_km": 50, "cruise_speed_kmh": 100,
            "takeoff_distance_m": 0, "power_type": "electric", "vtol": True,
        },
        design_rule_set="evtol_multi_rotor",
        material_scope=["carbon_fiber", "aluminum", "composite"],
        certification_standards=["CCAR-21", "ASTM-F3309"],
        default_settings={"design_margin": 2.0, "max_operating_speed_kmh": 150},
    ),
    AircraftTemplate(
        name="eVTOL - 倾转旋翼",
        aircraft_type="evtol",
        layout_type="tilt_rotor",
        description="倾转旋翼eVTOL，兼具垂直起降和高速巡航能力",
        default_spec={
            "payload_kg": 400, "range_km": 150, "cruise_speed_kmh": 250,
            "takeoff_distance_m": 0, "power_type": "electric", "vtol": True,
        },
        design_rule_set="evtol_tilt_rotor",
        material_scope=["carbon_fiber", "titanium", "composite"],
        certification_standards=["CCAR-21", "ASTM-F3309"],
        default_settings={"design_margin": 2.0, "max_operating_speed_kmh": 300},
    ),
    AircraftTemplate(
        name="eVTOL - 推力矢量",
        aircraft_type="evtol",
        layout_type="thrust_vector",
        description="推力矢量eVTOL，高机动垂直起降",
        default_spec={
            "payload_kg": 300, "range_km": 100, "cruise_speed_kmh": 200,
            "takeoff_distance_m": 0, "power_type": "electric", "vtol": True,
        },
        design_rule_set="evtol_thrust_vector",
        material_scope=["carbon_fiber", "titanium", "composite"],
        certification_standards=["CCAR-21"],
        default_settings={"design_margin": 2.0, "max_operating_speed_kmh": 250},
    ),
    AircraftTemplate(
        name="滑翔机 - 标准级",
        aircraft_type="glider",
        layout_type="standard_class",
        description="标准级滑翔机，高升阻比设计",
        default_spec={
            "payload_kg": 100, "range_km": 500, "cruise_speed_kmh": 80,
            "takeoff_distance_m": 200, "power_type": "none",
        },
        design_rule_set="glider_standard",
        material_scope=["carbon_fiber", "fiberglass", "composite"],
        certification_standards=["CS-22"],
        default_settings={"design_margin": 1.5, "max_operating_speed_kmh": 150},
    ),
    AircraftTemplate(
        name="滑翔机 - 开放级",
        aircraft_type="glider",
        layout_type="open_class",
        description="开放级滑翔机，极限性能设计",
        default_spec={
            "payload_kg": 120, "range_km": 1000, "cruise_speed_kmh": 100,
            "takeoff_distance_m": 300, "power_type": "none",
        },
        design_rule_set="glider_open",
        material_scope=["carbon_fiber", "composite"],
        certification_standards=["CS-22"],
        default_settings={"design_margin": 1.8, "max_operating_speed_kmh": 180},
    ),
    AircraftTemplate(
        name="无人机 - 多旋翼",
        aircraft_type="uav",
        layout_type="multi_rotor",
        description="多旋翼无人机，航拍/巡检用途",
        default_spec={
            "payload_kg": 5, "range_km": 10, "cruise_speed_kmh": 60,
            "takeoff_distance_m": 0, "power_type": "electric",
        },
        design_rule_set="uav_multi_rotor",
        material_scope=["carbon_fiber", "plastic", "aluminum"],
        certification_standards=["CCAR-92"],
        default_settings={"design_margin": 1.5, "max_operating_speed_kmh": 80},
    ),
    AircraftTemplate(
        name="无人机 - 固定翼",
        aircraft_type="uav",
        layout_type="conventional",
        description="固定翼无人机，长航时巡检/测绘",
        default_spec={
            "payload_kg": 10, "range_km": 200, "cruise_speed_kmh": 100,
            "takeoff_distance_m": 50, "power_type": "electric",
        },
        design_rule_set="uav_fixed_wing",
        material_scope=["carbon_fiber", "fiberglass", "composite"],
        certification_standards=["CCAR-92"],
        default_settings={"design_margin": 1.5, "max_operating_speed_kmh": 150},
    ),
    AircraftTemplate(
        name="无人机 - 垂直起降",
        aircraft_type="uav",
        layout_type="vtol_fixed_wing",
        description="垂直起降固定翼无人机，兼顾续航和起降灵活性",
        default_spec={
            "payload_kg": 8, "range_km": 100, "cruise_speed_kmh": 80,
            "takeoff_distance_m": 0, "power_type": "electric", "vtol": True,
        },
        design_rule_set="uav_vtol",
        material_scope=["carbon_fiber", "composite", "aluminum"],
        certification_standards=["CCAR-92"],
        default_settings={"design_margin": 1.5, "max_operating_speed_kmh": 120},
    ),
]


class TemplateRepository:
    def __init__(self) -> None:
        self._templates: dict[str, AircraftTemplate] = {t.id: t for t in BUILTIN_TEMPLATES}

    def get(self, template_id: str) -> AircraftTemplate | None:
        return self._templates.get(template_id)

    def list_templates(
        self,
        aircraft_type: str | None = None,
        layout_type: str | None = None,
    ) -> list[AircraftTemplate]:
        templates = list(self._templates.values())
        if aircraft_type:
            templates = [t for t in templates if t.aircraft_type == aircraft_type]
        if layout_type:
            templates = [t for t in templates if t.layout_type == layout_type]
        return templates

    def add_template(self, template: AircraftTemplate) -> None:
        self._templates[template.id] = template