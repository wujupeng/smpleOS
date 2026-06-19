from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProcessStep:
    def __init__(self, step_id: str, step_number: int, operation: str, equipment: str, estimated_time_hours: float, capabilities_required: list[str] | None = None):
        self.step_id = step_id
        self.step_number = step_number
        self.operation = operation
        self.equipment = equipment
        self.estimated_time_hours = estimated_time_hours
        self.capabilities_required = capabilities_required or []
        self.is_feasible = True
        self.alternative_suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "operation": self.operation,
            "equipment": self.equipment,
            "estimated_time_hours": self.estimated_time_hours,
            "capabilities_required": self.capabilities_required,
            "is_feasible": self.is_feasible,
            "alternative_suggestion": self.alternative_suggestion,
        }


class ProcessRoute:
    def __init__(self, route_id: str, component_type: str):
        self.route_id = route_id
        self.component_type = component_type
        self.steps: list[ProcessStep] = []
        self.total_estimated_hours: float = 0.0
        self.feasibility_status: str = "feasible"

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "component_type": self.component_type,
            "steps": [s.to_dict() for s in self.steps],
            "total_estimated_hours": self.total_estimated_hours,
            "feasibility_status": self.feasibility_status,
        }


class TravelerTemplate:
    def __init__(self, template_id: str, component_type: str):
        self.template_id = template_id
        self.component_type = component_type
        self.fields: list[dict[str, Any]] = []
        self.inspection_points: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "component_type": self.component_type,
            "fields": self.fields,
            "inspection_points": self.inspection_points,
        }


class NDTPlan:
    def __init__(self, plan_id: str, component_type: str):
        self.plan_id = plan_id
        self.component_type = component_type
        self.inspections: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "component_type": self.component_type,
            "inspections": self.inspections,
        }


class ManufacturingCapability:
    def __init__(self, capability_id: str, name: str, equipment: list[str], max_dimensions: dict[str, float], tolerances: dict[str, float]):
        self.capability_id = capability_id
        self.name = name
        self.equipment = equipment
        self.max_dimensions = max_dimensions
        self.tolerances = tolerances


DEFAULT_CAPABILITIES = [
    ManufacturingCapability("CAP-001", "CNC Milling", ["5-axis CNC"], {"length_m": 5.0, "width_m": 2.0}, {"linear_mm": 0.01, "angular_deg": 0.05}),
    ManufacturingCapability("CAP-002", "Autoclave Curing", ["Autoclave A1"], {"length_m": 10.0, "diameter_m": 3.0}, {"thickness_mm": 0.1}),
    ManufacturingCapability("CAP-003", "Composite Layup", ["Layup Station"], {"length_m": 15.0, "width_m": 5.0}, {"thickness_mm": 0.2}),
    ManufacturingCapability("CAP-004", "Friction Stir Welding", ["FSW-01"], {"length_m": 8.0, "thickness_m": 0.05}, {"linear_mm": 0.05}),
    ManufacturingCapability("CAP-005", "NDT Inspection", ["UT Scanner", "X-Ray"], {"length_m": 12.0, "diameter_m": 4.0}, {}),
]


class AeroGPTManufacturing:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._capabilities = list(DEFAULT_CAPABILITIES)
        self._routes: dict[str, ProcessRoute] = {}
        self._templates: dict[str, TravelerTemplate] = {}
        self._ndt_plans: dict[str, NDTPlan] = {}

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def generate_process_route(self, component_type: str, material: str, dimensions: dict[str, float]) -> ProcessRoute:
        route = ProcessRoute(route_id=str(uuid4()), component_type=component_type)
        step_num = 1

        if component_type == "wing_spar":
            if material.startswith("composite"):
                steps = [
                    ("Material Preparation", "Cutting Station", 2.0, ["composite_cutting"]),
                    ("Layup", "Layup Station", 8.0, ["composite_layup"]),
                    ("Curing", "Autoclave A1", 12.0, ["autoclave_curing"]),
                    ("Demolding", "Demolding Station", 2.0, []),
                    ("Machining", "5-axis CNC", 4.0, ["cnc_milling"]),
                    ("NDT Inspection", "UT Scanner", 3.0, ["ndt_inspection"]),
                    ("Surface Treatment", "Paint Booth", 2.0, []),
                ]
            else:
                steps = [
                    ("Material Cutting", "Waterjet Cutter", 1.5, ["cutting"]),
                    ("Forming", "Hydraulic Press", 3.0, ["forming"]),
                    ("Machining", "5-axis CNC", 6.0, ["cnc_milling"]),
                    ("Heat Treatment", "Furnace", 8.0, ["heat_treatment"]),
                    ("NDT Inspection", "UT Scanner", 2.0, ["ndt_inspection"]),
                    ("Surface Treatment", "Anodizing Line", 4.0, []),
                ]
        elif component_type == "wing_rib":
            steps = [
                ("Material Cutting", "Waterjet Cutter", 0.5, ["cutting"]),
                ("CNC Machining", "5-axis CNC", 1.5, ["cnc_milling"]),
                ("Deburring", "Manual Station", 0.5, []),
                ("NDT Inspection", "UT Scanner", 0.5, ["ndt_inspection"]),
            ]
        elif component_type == "fuselage_frame":
            steps = [
                ("Material Cutting", "Laser Cutter", 0.3, ["cutting"]),
                ("Forming", "Roll Former", 1.0, ["forming"]),
                ("Machining", "3-axis CNC", 1.0, ["cnc_milling"]),
                ("NDT Inspection", "ET Scanner", 0.5, ["ndt_inspection"]),
            ]
        elif component_type == "center_wing_box":
            steps = [
                ("Panel Fabrication", "Layup Station", 6.0, ["composite_layup"]),
                ("Panel Curing", "Autoclave A1", 10.0, ["autoclave_curing"]),
                ("Assembly", "Assembly Jig", 8.0, ["assembly"]),
                ("Fastening", "FSW-01", 4.0, ["friction_stir_welding"]),
                ("NDT Inspection", "X-Ray", 4.0, ["ndt_inspection"]),
                ("Sealing", "Sealant Station", 2.0, []),
            ]
        else:
            steps = [
                ("Material Preparation", "General Station", 2.0, []),
                ("Primary Processing", "General Equipment", 4.0, []),
                ("Inspection", "QC Station", 1.0, []),
            ]

        for operation, equipment, est_time, capabilities in steps:
            step = ProcessStep(
                step_id=f"STEP-{step_num:03d}",
                step_number=step_num,
                operation=operation,
                equipment=equipment,
                estimated_time_hours=est_time,
                capabilities_required=capabilities,
            )
            step.is_feasible = self._check_capability_feasibility(capabilities, dimensions)
            if not step.is_feasible:
                step.alternative_suggestion = self._suggest_alternative(capabilities, dimensions)
            route.steps.append(step)
            step_num += 1

        route.total_estimated_hours = sum(s.estimated_time_hours for s in route.steps)
        infeasible_count = sum(1 for s in route.steps if not s.is_feasible)
        route.feasibility_status = "feasible" if infeasible_count == 0 else "partially_feasible" if infeasible_count < len(route.steps) else "infeasible"

        self._routes[route.route_id] = route
        return route

    def generate_traveler_template(self, component_type: str, process_route: ProcessRoute) -> TravelerTemplate:
        template = TravelerTemplate(template_id=str(uuid4()), component_type=component_type)

        template.fields = [
            {"name": "component_serial_number", "type": "text", "required": True, "prefilled": False},
            {"name": "work_order_id", "type": "text", "required": True, "prefilled": False},
            {"name": "component_type", "type": "text", "required": True, "prefilled": True, "value": component_type},
            {"name": "material", "type": "text", "required": True, "prefilled": False},
            {"name": "operator_id", "type": "text", "required": True, "prefilled": False},
            {"name": "start_date", "type": "datetime", "required": True, "prefilled": False},
            {"name": "completion_date", "type": "datetime", "required": False, "prefilled": False},
        ]

        for step in process_route.steps:
            template.fields.append({
                "name": f"step_{step.step_number}_status",
                "type": "select",
                "options": ["pending", "in_progress", "completed", "failed"],
                "required": True,
                "prefilled": True,
                "value": "pending",
            })
            template.inspection_points.append({
                "step_number": step.step_number,
                "operation": step.operation,
                "inspection_type": "dimensional" if "machining" in step.operation.lower() or "forming" in step.operation.lower() else "visual",
                "acceptance_criteria": "Per engineering drawing",
            })

        self._templates[template.template_id] = template
        return template

    def generate_ndt_plan(self, component_type: str, material: str, critical_areas: list[str] | None = None) -> NDTPlan:
        plan = NDTPlan(plan_id=str(uuid4()), component_type=component_type)
        critical = critical_areas or []

        if material.startswith("composite"):
            plan.inspections = [
                {"area": "general", "method": "ultrasonic", "type": "pulse_echo", "acceptance": "No delamination > 10mm", "critical": False},
                {"area": "bonded_joints" if "joints" in critical else "general", "method": "ultrasonic", "type": "through_transmission", "acceptance": "No disbonds", "critical": True},
                {"area": "general", "method": "visual", "type": "surface", "acceptance": "No visible defects", "critical": False},
            ]
        else:
            plan.inspections = [
                {"area": "general", "method": "ultrasonic", "type": "pulse_echo", "acceptance": "No internal defects > 2mm", "critical": False},
                {"area": "welds" if "welds" in critical else "general", "method": "radiographic", "type": "x-ray", "acceptance": "No cracks or porosity", "critical": True},
                {"area": "surface", "method": "eddy_current", "type": "surface", "acceptance": "No surface cracks", "critical": False},
                {"area": "general", "method": "visual", "type": "surface", "acceptance": "No visible defects", "critical": False},
            ]

        for area in critical:
            if not any(i["area"] == area for i in plan.inspections):
                plan.inspections.append({
                    "area": area,
                    "method": "ultrasonic",
                    "type": "pulse_echo",
                    "acceptance": "Per engineering specification",
                    "critical": True,
                })

        self._ndt_plans[plan.plan_id] = plan
        return plan

    def _check_capability_feasibility(self, required_capabilities: list[str], dimensions: dict[str, float]) -> bool:
        if not required_capabilities:
            return True
        available = set()
        for cap in self._capabilities:
            available.update([cap.name.lower().replace(" ", "_")])
        for req in required_capabilities:
            if req.lower() not in available:
                return False
        return True

    def _suggest_alternative(self, required_capabilities: list[str], dimensions: dict[str, float]) -> str:
        for req in required_capabilities:
            if req == "autoclave_curing":
                return "Consider out-of-autoclave (OOA) curing process or outsource to facility with larger autoclave"
            if req == "cnc_milling":
                return "Consider outsourcing CNC machining to certified supplier"
        return "Consider alternative manufacturing process or outsource to qualified supplier"

    def get_route(self, route_id: str) -> ProcessRoute | None:
        return self._routes.get(route_id)

    def get_template(self, template_id: str) -> TravelerTemplate | None:
        return self._templates.get(template_id)

    def get_ndt_plan(self, plan_id: str) -> NDTPlan | None:
        return self._ndt_plans.get(plan_id)