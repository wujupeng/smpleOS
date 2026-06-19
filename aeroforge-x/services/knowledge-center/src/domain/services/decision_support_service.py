from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any


class IntelligentRecommendationService:
    def __init__(self) -> None:
        self._recommendation_history: list[dict[str, Any]] = []

    def recommend_design_parameters(
        self,
        tenant_id: str,
        project_id: str,
        design_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        recommendations = [
            {
                "parameter": "wing_span",
                "recommended_value": 15.2,
                "unit": "m",
                "range": {"min": 12.0, "max": 18.0},
                "reason": "Based on similar aircraft in knowledge graph with comparable MTOW",
                "evidence_refs": ["KG-REG-001", "KG-DESIGN-005"],
                "confidence": 0.92,
            },
            {
                "parameter": "CL_max",
                "recommended_value": 1.65,
                "unit": "",
                "range": {"min": 1.5, "max": 2.0},
                "reason": "FAR-23 §23.201 requires CL_max >= 1.5, historical average 1.65",
                "evidence_refs": ["KG-REG-001"],
                "confidence": 0.88,
            },
            {
                "parameter": "safety_factor",
                "recommended_value": 1.5,
                "unit": "",
                "range": {"min": 1.5, "max": 2.0},
                "reason": "FAR-25 §25.305 minimum safety factor requirement",
                "evidence_refs": ["KG-REG-003"],
                "confidence": 0.95,
            },
        ]

        result = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "recommendation_type": "design_parameters",
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._recommendation_history.append(result)
        return result

    def recommend_material_selection(
        self,
        tenant_id: str,
        project_id: str,
        requirements: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        materials = [
            {
                "material": "Ti-6Al-4V",
                "score": 0.92,
                "pros": ["High strength-to-weight ratio", "Excellent corrosion resistance", "Certified for aerospace"],
                "cons": ["High cost", "Difficult to machine"],
                "applicable_processes": ["Isothermal Forging", "Conventional Forging"],
                "certification_status": "certified",
                "supply_availability": "good",
            },
            {
                "material": "Al 7075-T6",
                "score": 0.85,
                "pros": ["Good strength", "Lower cost", "Easy to machine"],
                "cons": ["Lower temperature capability", "Stress corrosion susceptibility"],
                "applicable_processes": ["Conventional Forging"],
                "certification_status": "certified",
                "supply_availability": "excellent",
            },
            {
                "material": "Inconel 718",
                "score": 0.78,
                "pros": ["Very high temperature capability", "Excellent creep resistance"],
                "cons": ["Very high cost", "Difficult to forge", "Heavy"],
                "applicable_processes": ["Isothermal Forging"],
                "certification_status": "certified",
                "supply_availability": "limited",
            },
        ]

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "recommendation_type": "material_selection",
            "materials": sorted(materials, key=lambda m: m["score"], reverse=True),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def recommend_process_parameters(
        self,
        tenant_id: str,
        project_id: str,
        material: str = "Ti-6Al-4V",
    ) -> dict[str, Any]:
        process_recs = {
            "Ti-6Al-4V": {
                "process": "Isothermal Forging",
                "parameters": [
                    {"name": "forging_temperature", "value": 950, "unit": "°C", "range": "900-980"},
                    {"name": "strain_rate", "value": 0.01, "unit": "/s", "range": "0.001-0.1"},
                    {"name": "die_temperature", "value": 940, "unit": "°C", "range": "900-960"},
                ],
            },
            "Al 7075-T6": {
                "process": "Conventional Forging",
                "parameters": [
                    {"name": "forging_temperature", "value": 430, "unit": "°C", "range": "380-460"},
                    {"name": "strain_rate", "value": 10, "unit": "/s", "range": "1-50"},
                    {"name": "die_temperature", "value": 400, "unit": "°C", "range": "350-440"},
                ],
            },
        }

        rec = process_recs.get(material, process_recs["Ti-6Al-4V"])

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "recommendation_type": "process_parameters",
            "material": material,
            "recommended_process": rec["process"],
            "parameters": rec["parameters"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def recommend_failure_prevention(
        self,
        tenant_id: str,
        project_id: str,
        component_type: str = "forged_part",
    ) -> dict[str, Any]:
        preventions = [
            {
                "failure_mode": "Forging Crack",
                "severity": "high",
                "prevention_measures": [
                    "Control strain rate below 0.1/s for Ti-6Al-4V",
                    "Maintain uniform temperature distribution",
                    "Use isothermal forging for difficult-to-forge alloys",
                ],
                "monitoring": "Ultrasonic inspection after forging",
                "evidence_refs": ["KG-FM-001", "KG-PROC-001"],
            },
            {
                "failure_mode": "Residual Stress Distortion",
                "severity": "medium",
                "prevention_measures": [
                    "Implement controlled cooling after forging",
                    "Apply stress relief heat treatment",
                    "Use simulation to predict distortion",
                ],
                "monitoring": "Dimensional inspection after heat treatment",
                "evidence_refs": ["KG-FM-002"],
            },
        ]

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "recommendation_type": "failure_prevention",
            "preventions": preventions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


class DecisionSupportService:
    def __init__(self) -> None:
        self._decisions: list[dict[str, Any]] = []

    def support_design_decision(
        self,
        tenant_id: str,
        project_id: str,
        alternatives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        alts = alternatives or [
            {"name": "Option A: Conventional Design", "description": "Proven design with established processes"},
            {"name": "Option B: Optimized Design", "description": "Lightweight design with advanced materials"},
            {"name": "Option C: Conservative Design", "description": "Higher safety margins, easier certification"},
        ]

        comparison = []
        for alt in alts:
            comparison.append({
                "name": alt["name"],
                "performance_score": round(random.uniform(0.6, 0.95), 2),
                "cost_score": round(random.uniform(0.5, 0.9), 2),
                "risk_score": round(random.uniform(0.3, 0.8), 2),
                "certification_ease": round(random.uniform(0.5, 0.95), 2),
                "overall_score": round(random.uniform(0.6, 0.9), 2),
            })

        comparison.sort(key=lambda c: c["overall_score"], reverse=True)

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "decision_type": "design",
            "alternatives_comparison": comparison,
            "recommended": comparison[0]["name"],
            "recommendation_reason": "Best overall balance of performance, cost, risk, and certification ease",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def support_make_or_buy_decision(
        self,
        tenant_id: str,
        project_id: str,
        component: str = "forged_billet",
    ) -> dict[str, Any]:
        make_cost = random.uniform(50000, 150000)
        buy_cost = random.uniform(60000, 180000)

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "decision_type": "make_or_buy",
            "component": component,
            "make_analysis": {
                "cost": round(make_cost, 2),
                "lead_time_weeks": random.randint(8, 20),
                "quality_control": "high",
                "ip_protection": "strong",
                "capacity_required": "significant",
            },
            "buy_analysis": {
                "cost": round(buy_cost, 2),
                "lead_time_weeks": random.randint(4, 12),
                "quality_control": "moderate",
                "ip_protection": "limited",
                "supplier_dependency": "high",
            },
            "recommendation": "make" if make_cost < buy_cost * 0.9 else "buy",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def support_supplier_selection_decision(
        self,
        tenant_id: str,
        project_id: str,
        material: str = "titanium_alloy",
    ) -> dict[str, Any]:
        suppliers = [
            {"supplier_id": "SUP-001", "name": "AeroForge Materials", "quality": 0.95, "delivery": 0.88, "cost": 0.82, "risk": 0.15},
            {"supplier_id": "SUP-002", "name": "Precision Forging Ltd.", "quality": 0.90, "delivery": 0.92, "cost": 0.78, "risk": 0.20},
            {"supplier_id": "SUP-005", "name": "Raw Metal Suppliers", "quality": 0.85, "delivery": 0.85, "cost": 0.90, "risk": 0.25},
        ]

        for s in suppliers:
            s["overall_score"] = round(s["quality"] * 0.35 + s["delivery"] * 0.25 + s["cost"] * 0.25 + (1 - s["risk"]) * 0.15, 4)

        suppliers.sort(key=lambda s: s["overall_score"], reverse=True)

        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "decision_type": "supplier_selection",
            "material": material,
            "suppliers": suppliers,
            "recommended": suppliers[0]["supplier_id"],
            "risk_diversification_strategy": "Split 70/30 between top 2 suppliers",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_decision_report(
        self,
        tenant_id: str,
        project_id: str,
        decision_type: str,
    ) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "report_type": "decision_report",
            "decision_type": decision_type,
            "sections": [
                {"title": "Decision Background", "content": f"Analysis for {decision_type} decision"},
                {"title": "Alternatives Comparison", "content": "Quantitative comparison of all alternatives"},
                {"title": "Recommendation", "content": "Recommended option with justification"},
                {"title": "Risk Assessment", "content": "Risk factors and mitigation strategies"},
                {"title": "Knowledge Evidence", "content": "References to knowledge graph evidence"},
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }