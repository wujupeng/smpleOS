from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AnalyticsDomainService:
    def __init__(self) -> None:
        self._design_data: dict[str, list[dict[str, Any]]] = {}
        self._manufacturing_data: dict[str, list[dict[str, Any]]] = {}
        self._quality_data: dict[str, list[dict[str, Any]]] = {}
        self._trace_data: dict[str, list[dict[str, Any]]] = {}
        self._supply_data: dict[str, list[dict[str, Any]]] = {}

    def add_design_record(self, project_id: str, record: dict[str, Any]) -> None:
        self._design_data.setdefault(project_id, []).append(record)

    def add_manufacturing_record(self, project_id: str, record: dict[str, Any]) -> None:
        self._manufacturing_data.setdefault(project_id, []).append(record)

    def add_quality_record(self, project_id: str, record: dict[str, Any]) -> None:
        self._quality_data.setdefault(project_id, []).append(record)

    def add_trace_record(self, project_id: str, record: dict[str, Any]) -> None:
        self._trace_data.setdefault(project_id, []).append(record)

    def add_supply_record(self, project_id: str, record: dict[str, Any]) -> None:
        self._supply_data.setdefault(project_id, []).append(record)

    def query_design_metrics(self, project_id: str | None = None) -> dict[str, Any]:
        records = self._get_records(self._design_data, project_id)
        if not records:
            return self._empty_metrics("design")

        total = len(records)
        completed = sum(1 for r in records if r.get("status") == "completed")
        violations = sum(1 for r in records if r.get("has_violation"))
        cae_completed = sum(1 for r in records if r.get("cae_status") == "completed")
        cae_total = sum(1 for r in records if "cae_status" in r)
        iterations = sum(r.get("iteration_count", 0) for r in records)

        return {
            "total_projects": len(set(r.get("project_id", "") for r in records)),
            "design_progress_pct": round(completed / max(total, 1) * 100, 1),
            "violation_rate": round(violations / max(total, 1) * 100, 1),
            "cae_completion_rate": round(cae_completed / max(cae_total, 1) * 100, 1),
            "avg_iterations": round(iterations / max(total, 1), 1),
            "violation_trend": self._compute_trend(records, "has_violation"),
            "cae_time_trend": self._compute_trend(records, "cae_duration_hours"),
        }

    def query_manufacturing_metrics(self, project_id: str | None = None) -> dict[str, Any]:
        records = self._get_records(self._manufacturing_data, project_id)
        if not records:
            return self._empty_metrics("manufacturing")

        total = len(records)
        completed = sum(1 for r in records if r.get("status") == "completed")
        on_time = sum(1 for r in records if r.get("on_time"))
        ws_util = [r.get("utilization_pct", 0) for r in records if "utilization_pct" in r]
        deviations = [r.get("deviation_mm", 0) for r in records if "deviation_mm" in r]

        return {
            "work_order_completion_rate": round(completed / max(total, 1) * 100, 1),
            "on_time_rate": round(on_time / max(total, 1) * 100, 1),
            "avg_workstation_utilization": round(sum(ws_util) / max(len(ws_util), 1), 1),
            "avg_deviation_mm": round(sum(deviations) / max(len(deviations), 1), 3),
            "completion_trend": self._compute_trend(records, "status", target="completed"),
            "deviation_distribution": self._compute_distribution(deviations),
        }

    def query_quality_metrics(self, project_id: str | None = None) -> dict[str, Any]:
        records = self._get_records(self._quality_data, project_id)
        if not records:
            return self._empty_metrics("quality")

        total = len(records)
        iqc_pass = sum(1 for r in records if r.get("iqc_passed"))
        capa_closed = sum(1 for r in records if r.get("capa_status") == "closed")
        capa_total = sum(1 for r in records if "capa_status" in r)
        cpk_values = [r.get("cpk", 0) for r in records if "cpk" in r]
        nc_items = [(r.get("nc_category", "unknown"), r.get("nc_count", 1)) for r in records if r.get("is_nc")]

        nc_pareto = self._compute_pareto(nc_items)

        return {
            "iqc_pass_rate": round(iqc_pass / max(total, 1) * 100, 1),
            "capa_close_rate": round(capa_closed / max(capa_total, 1) * 100, 1),
            "avg_cpk": round(sum(cpk_values) / max(len(cpk_values), 1), 2),
            "cpk_trend": self._compute_trend(records, "cpk"),
            "nc_pareto": nc_pareto,
        }

    def query_traceability_metrics(self, project_id: str | None = None) -> dict[str, Any]:
        records = self._get_records(self._trace_data, project_id)
        if not records:
            return self._empty_metrics("traceability")

        total = len(records)
        complete = sum(1 for r in records if r.get("is_complete"))
        response_times = [r.get("query_time_ms", 0) for r in records if "query_time_ms" in r]
        recall_ranges = [r.get("recall_scope", 0) for r in records if "recall_scope" in r]

        return {
            "trace_completeness_rate": round(complete / max(total, 1) * 100, 1),
            "avg_query_time_ms": round(sum(response_times) / max(len(response_times), 1), 1),
            "avg_recall_scope": round(sum(recall_ranges) / max(len(recall_ranges), 1), 1),
        }

    def query_supply_chain_metrics(self, project_id: str | None = None) -> dict[str, Any:
        records = self._get_records(self._supply_data, project_id)
        if not records:
            return self._empty_metrics("supply_chain")

        supplier_scores: dict[str, list[float]] = {}
        for r in records:
            sid = r.get("supplier_id", "unknown")
            score = r.get("performance_score", 0)
            supplier_scores.setdefault(sid, []).append(score)

        supplier_ranking = sorted(
            [(sid, sum(scores) / len(scores)) for sid, scores in supplier_scores.items()],
            key=lambda x: x[1], reverse=True,
        )

        total_orders = len(records)
        on_time_orders = sum(1 for r in records if r.get("on_time"))
        turnover = [r.get("turnover_rate", 0) for r in records if "turnover_rate" in r]
        shortage_impact = sum(r.get("shortage_affected_wo", 0) for r in records if "shortage_affected_wo" in r)

        return {
            "supplier_ranking": [{"supplier_id": s[0], "avg_score": round(s[1], 2)} for s in supplier_ranking[:10]],
            "po_on_time_rate": round(on_time_orders / max(total_orders, 1) * 100, 1),
            "avg_inventory_turnover": round(sum(turnover) / max(len(turnover), 1), 2),
            "shortage_affected_wo": shortage_impact,
        }

    def cross_domain_analysis(self, project_id: str | None = None) -> dict[str, Any]:
        design = self.query_design_metrics(project_id)
        mfg = self.query_manufacturing_metrics(project_id)
        quality = self.query_quality_metrics(project_id)
        supply = self.query_supply_chain_metrics(project_id)

        design_change_impact = []
        violation_rate = design.get("violation_rate", 0)
        if violation_rate > 10:
            design_change_impact.append({
                "source": "design_violation",
                "impact": "manufacturing_deviation",
                "correlation": "high",
                "description": f"设计违规率{violation_rate}%偏高，可能导致制造偏差增大",
            })

        supplier_quality = supply.get("supplier_ranking", [])
        low_score_suppliers = [s for s in supplier_quality if s.get("avg_score", 0) < 0.7]
        if low_score_suppliers:
            design_change_impact.append({
                "source": "supplier_quality",
                "impact": "incoming_quality",
                "correlation": "medium",
                "description": f"{len(low_score_suppliers)}个供应商绩效低于0.7，可能影响来料质量",
            })

        return {
            "design_metrics_summary": design,
            "manufacturing_metrics_summary": mfg,
            "quality_metrics_summary": quality,
            "supply_chain_metrics_summary": supply,
            "cross_domain_links": design_change_impact,
        }

    def _get_records(self, data: dict[str, list[dict[str, Any]]], project_id: str | None) -> list[dict[str, Any]]:
        if project_id:
            return data.get(project_id, [])
        all_records = []
        for records in data.values():
            all_records.extend(records)
        return all_records

    def _empty_metrics(self, domain: str) -> dict[str, Any]:
        return {"domain": domain, "message": "no data available"}

    def _compute_trend(self, records: list[dict[str, Any]], key: str, target: str | None = None) -> list[dict[str, Any]]:
        trend = []
        for i, r in enumerate(records[-10:]):
            val = r.get(key)
            if target:
                val = 1 if val == target else 0
            trend.append({"index": i + 1, "value": val})
        return trend

    def _compute_distribution(self, values: list[float]) -> dict[str, int]:
        if not values:
            return {}
        bins = {"<0.01": 0, "0.01-0.05": 0, "0.05-0.1": 0, ">0.1": 0}
        for v in values:
            if v < 0.01:
                bins["<0.01"] += 1
            elif v < 0.05:
                bins["0.01-0.05"] += 1
            elif v < 0.1:
                bins["0.05-0.1"] += 1
            else:
                bins[">0.1"] += 1
        return bins

    def _compute_pareto(self, items: list[tuple[str, int]]) -> list[dict[str, Any]]:
        if not items:
            return []
        category_totals: dict[str, int] = {}
        for cat, count in items:
            category_totals[cat] = category_totals.get(cat, 0) + count
        sorted_items = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        total = sum(v for _, v in sorted_items)
        cumulative = 0
        result = []
        for cat, count in sorted_items:
            cumulative += count
            result.append({
                "category": cat,
                "count": count,
                "pct": round(count / max(total, 1) * 100, 1),
                "cumulative_pct": round(cumulative / max(total, 1) * 100, 1),
            })
        return result