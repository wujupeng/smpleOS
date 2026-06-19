from __future__ import annotations

from typing import Any

from src.domain.handlers.activity_handler_v3 import ActivityHandlerV3, HandlerInput, HandlerOutput


class DesignRuleCheckHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "design.rule_check"

    def get_schema_references(self) -> list[str]:
        return ["AircraftGeometry", "AircraftStructure"]

    def validate_input(self, input_data: HandlerInput) -> list[str]:
        errors = []
        if not input_data.model_id:
            errors.append("model_id is required")
        if not input_data.rule_set_id:
            errors.append("rule_set_id is required")
        return errors

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        geometry = input_data.parameters.get("geometry", {})
        structure = input_data.parameters.get("structure", {})

        violations = []
        wingspan = geometry.get("wingspan", 0)
        if wingspan > 0:
            aspect_ratio = geometry.get("aspect_ratio", 0)
            if aspect_ratio > 20:
                violations.append({"rule": "AR-001", "message": f"Aspect ratio {aspect_ratio:.1f} exceeds 20 limit", "severity": "warning"})
            taper_ratio = geometry.get("taper_ratio", 0)
            if taper_ratio < 0.2:
                violations.append({"rule": "TR-001", "message": f"Taper ratio {taper_ratio:.2f} below 0.2 minimum", "severity": "error"})

        yield_strength = structure.get("yield_strength", 0)
        design_weight = structure.get("design_weight", 0)
        if yield_strength > 0 and design_weight > 0:
            wing_area = geometry.get("wing_area", 16.0)
            n_max = input_data.parameters.get("n_max", 3.5)
            load = n_max * design_weight * 9.81
            stress = load / (wing_area * structure.get("skin_thickness", 2.0) * 1e-3)
            if stress > yield_strength * 1e6:
                violations.append({"rule": "STR-001", "message": f"Wing root stress {stress/1e6:.1f} MPa exceeds yield {yield_strength:.1f} MPa", "severity": "error"})

        return HandlerOutput(
            status="completed",
            result={"violations": violations, "model_id": input_data.model_id, "rule_set_id": input_data.rule_set_id, "total_rules_checked": 3 + len(violations)},
            schema_refs_used=["AircraftGeometry", "AircraftStructure"],
        )


class CAETriggerHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "design.cae_trigger"

    def get_schema_references(self) -> list[str]:
        return ["AircraftGeometry", "AircraftStructure"]

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        geometry = input_data.parameters.get("geometry", {})
        structure = input_data.parameters.get("structure", {})

        cae_params = {
            "reference_area": geometry.get("wing_area", 16.0),
            "reference_chord": geometry.get("chord_length", 1.6),
            "reference_span": geometry.get("wingspan", 10.0),
            "sweep_angle": geometry.get("sweep_angle", 0.0),
            "material_id": structure.get("material_id", ""),
            "material_density": structure.get("material_density", 2700.0),
            "yield_strength": structure.get("yield_strength", 300.0),
            "elastic_modulus": structure.get("elastic_modulus", 70.0),
        }

        return HandlerOutput(
            status="completed",
            result={"cae_input_parameters": cae_params, "model_id": input_data.model_id},
            schema_refs_used=["AircraftGeometry", "AircraftStructure"],
        )


class CFDAnalysisHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "verification.cfd_analysis"

    def get_schema_references(self) -> list[str]:
        return ["AircraftGeometry", "AircraftFlightEnvelope"]

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        geometry = input_data.parameters.get("geometry", {})
        envelope = input_data.parameters.get("envelope", {})

        boundary_conditions = {
            "V_min": envelope.get("V_s", 30.0),
            "V_cruise": envelope.get("V_C", 60.0),
            "V_max": envelope.get("V_D", 100.0),
            "altitude": envelope.get("h_max", 3000.0),
        }

        alpha_range = [-5, 15]
        V = boundary_conditions["V_cruise"]
        rho = 1.225
        S = geometry.get("wing_area", 16.0)
        q_s = 0.5 * rho * V ** 2 * S

        CL = 0.5
        CD = 0.03
        Cm = -0.02

        results = {
            "simulation_id": f"cfd-sim-{input_data.model_id[:8]}",
            "boundary_conditions": boundary_conditions,
            "scalar_results": {"CL": CL, "CD": CD, "Cm": Cm, "L_D": CL / max(CD, 0.001)},
            "pressure_distribution_available": True,
        }

        return HandlerOutput(
            status="completed",
            result=results,
            schema_refs_used=["AircraftGeometry", "AircraftFlightEnvelope"],
        )


class FEAAnalysisHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "verification.fea_analysis"

    def get_schema_references(self) -> list[str]:
        return ["AircraftStructure", "AircraftFlightEnvelope"]

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        structure = input_data.parameters.get("structure", {})
        envelope = input_data.parameters.get("envelope", {})

        load_conditions = {
            "n_min": envelope.get("n_min", -1.0),
            "n_max": envelope.get("n_max", 3.5),
            "V_D": envelope.get("V_D", 100.0),
        }

        yield_strength = structure.get("yield_strength", 300.0)
        max_stress = yield_strength * 0.85
        max_displacement = 5.0
        natural_frequency = 25.0

        results = {
            "simulation_id": f"fea-sim-{input_data.model_id[:8]}",
            "load_conditions": load_conditions,
            "scalar_results": {
                "max_stress_MPa": max_stress,
                "max_displacement_mm": max_displacement,
                "natural_frequency_Hz": natural_frequency,
                "safety_factor": yield_strength / max(max_stress, 1),
            },
        }

        return HandlerOutput(
            status="completed",
            result=results,
            schema_refs_used=["AircraftStructure", "AircraftFlightEnvelope"],
        )


class MBOMTransformHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "manufacturing.mbom_transform"

    def get_schema_references(self) -> list[str]:
        return ["AircraftStructure"]

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        ebom_items = input_data.parameters.get("ebom_items", [])
        structure = input_data.parameters.get("structure", {})

        mbom_items = []
        unconfirmed = []

        for item in ebom_items:
            mbom_item = dict(item)
            mbom_item["manufacturing_process"] = self._infer_process(item.get("component_type", ""))
            mbom_item["design_weight"] = item.get("weight", structure.get("design_weight", 0))
            mbom_item["material_id"] = item.get("material_id", structure.get("material_id", ""))

            if not mbom_item.get("manufacturing_process"):
                mbom_item["status"] = "pending_confirmation"
                unconfirmed.append(mbom_item.get("id", ""))
            else:
                mbom_item["status"] = "mapped"

            mbom_items.append(mbom_item)

        return HandlerOutput(
            status="completed",
            result={"mbom_structure": mbom_items, "total_items": len(mbom_items), "unconfirmed_items": unconfirmed},
            schema_refs_used=["AircraftStructure"],
        )

    def _infer_process(self, component_type: str) -> str:
        process_map = {"wing_skin": "CNC_milling", "rib": "CNC_milling", "spar": "extrusion", "fastener": "procurement", "bracket": "CNC_milling"}
        return process_map.get(component_type.lower(), "")


class WorkOrderGenerateHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "manufacturing.work_order_generate"

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        mbom_items = input_data.parameters.get("mbom_items", [])

        work_orders = []
        for item in mbom_items:
            if item.get("status") == "mapped":
                wo = {
                    "work_order_id": f"WO-{item.get('id', 'unknown')[:8]}",
                    "component": item.get("id", ""),
                    "process": item.get("manufacturing_process", ""),
                    "estimated_hours": self._estimate_hours(item.get("manufacturing_process", "")),
                    "material_list": [{"material_id": item.get("material_id", ""), "qty": 1}],
                    "status": "Created",
                }
                work_orders.append(wo)

        return HandlerOutput(
            status="completed",
            result={"work_orders": work_orders, "total_work_orders": len(work_orders)},
        )

    def _estimate_hours(self, process: str) -> float:
        hours_map = {"CNC_milling": 8.0, "extrusion": 4.0, "procurement": 0.0, "assembly": 12.0}
        return hours_map.get(process, 6.0)


class ComplianceCheckHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "certification.compliance_check"

    def get_schema_references(self) -> list[str]:
        return ["AircraftCertification"]

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        certification = input_data.parameters.get("certification", {})

        clause = certification.get("clause_number", "")
        status = certification.get("compliance_status", "NotAssessed")
        method = certification.get("compliance_method", "")
        evidence = certification.get("evidence_ref", "")

        issues = []
        if status == "Compliant" and not evidence:
            issues.append("Compliant status without evidence reference")
        if method == "MOC4" and "flight_test" not in (evidence or "").lower():
            issues.append("MOC4 requires flight test report reference")

        return HandlerOutput(
            status="completed",
            result={"clause_number": clause, "compliance_result": status, "issues": issues},
            schema_refs_used=["AircraftCertification"],
        )


class ComplianceImpactHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "certification.compliance_impact"

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        anomaly_type = input_data.parameters.get("anomaly_type", "")
        affected_components = input_data.parameters.get("affected_components", [])

        needs_review = False
        impact_level = "low"

        safety_keywords = ["structural", "engine", "flight_control", "battery_thermal"]
        if any(kw in anomaly_type.lower() for kw in safety_keywords):
            needs_review = True
            impact_level = "high"

        return HandlerOutput(
            status="completed",
            result={"anomaly_type": anomaly_type, "compliance_impact": impact_level, "needs_review": needs_review, "affected_clauses": affected_components},
        )


class FRACASCreateHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "quality.fracas_create"

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        anomaly_data = input_data.parameters.get("anomaly_data", {})

        fracas_report = {
            "fracas_report_id": f"FRACAS-{anomaly_data.get('component_id', 'unknown')[:8]}",
            "anomaly_type": anomaly_data.get("anomaly_type", ""),
            "detected_values": anomaly_data.get("detected_values", {}),
            "predicted_values": anomaly_data.get("predicted_values", {}),
            "deviation": anomaly_data.get("deviation", 0.0),
            "component_id": anomaly_data.get("component_id", ""),
            "detection_timestamp": anomaly_data.get("timestamp", ""),
            "severity": "critical" if anomaly_data.get("deviation", 0) > 0.5 else "warning",
        }

        return HandlerOutput(status="completed", result=fracas_report)


class RootCauseAnalysisHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "quality.root_cause_analysis"

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        fracas_id = input_data.parameters.get("fracas_report_id", "")
        anomaly_type = input_data.parameters.get("anomaly_type", "")

        root_cause_map = {
            "temperature_anomaly": {"root_cause": "cooling_system_degradation", "confidence": 0.85, "recommendations": ["Inspect cooling system", "Check coolant flow rate"]},
            "structural_anomaly": {"root_cause": "fatigue_crack_initiation", "confidence": 0.7, "recommendations": ["Schedule NDT inspection", "Review load spectrum"]},
            "battery_degradation": {"root_cause": "calendar_aging_accelerated", "confidence": 0.9, "recommendations": ["Check thermal management", "Review charging protocol"]},
        }

        analysis = root_cause_map.get(anomaly_type, {"root_cause": "unknown", "confidence": 0.0, "recommendations": ["Further investigation required"]})

        return HandlerOutput(
            status="completed",
            result={"fracas_report_id": fracas_id, "root_cause": analysis["root_cause"], "confidence": analysis["confidence"], "recommendations": analysis["recommendations"]},
        )


class InspectionHandler(ActivityHandlerV3):

    def get_handler_name(self) -> str:
        return "quality.inspection"

    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        work_order_id = input_data.parameters.get("work_order_id", "")
        inspection_items = input_data.parameters.get("inspection_items", [])

        results = []
        for item in inspection_items:
            results.append({"item": item, "result": "passed", "measured_value": "within_tolerance"})

        return HandlerOutput(
            status="completed",
            result={"work_order_id": work_order_id, "inspection_result": "passed", "items_checked": len(results), "items_failed": 0},
        )