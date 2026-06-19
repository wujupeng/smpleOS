"""AeroForge-X v6.0 ObservabilityMetricsService

Provides Prometheus-compatible metrics for all v6.0 Programs.
Tracks latencies, durations, progress, and coverage percentages.

Metrics:
- config_propagation_duration_seconds (REQ-DFX-V6-018)
- checklist_generation_duration_seconds (REQ-DFX-V6-019)
- cert_evidence_assembly_duration_seconds (REQ-DFX-V6-020)
- supplier_rating_duration_seconds (REQ-DFX-V6-021)
- material_trace_duration_seconds (REQ-DFX-V6-022)
- shop_floor_collection_latency_seconds (REQ-DFX-V6-023)
- dashboard_update_latency_seconds (REQ-DFX-V6-024)
- uq_inference_duration_seconds (REQ-DFX-V6-025)
- mdo_7d_generation_progress (REQ-DFX-V6-026)
- traceability_coverage_percentage (REQ-DFX-V6-001)

REQ-DFX-V6-001
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MetricType(str, Enum):
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    COUNTER = "counter"


@dataclass
class MetricSample:
    metric_name: str
    metric_type: MetricType
    value: float
    labels: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class MetricSummary:
    metric_name: str
    count: int = 0
    sum: float = 0.0
    min: float = float("inf")
    max: float = float("-inf")
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "count": self.count,
            "sum": self.sum,
            "min": self.min,
            "max": self.max,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99,
        }


METRIC_DEFINITIONS = {
    "aircraft_core_config_propagation_duration_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Configuration three-view propagation duration",
        "unit": "seconds",
        "alert_p99": 10.0,
    },
    "aircraft_core_checklist_generation_duration_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Compliance checklist generation duration",
        "unit": "seconds",
        "alert_p99": 30.0,
    },
    "workflow_engine_cert_evidence_assembly_duration_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Certification evidence package assembly duration",
        "unit": "seconds",
        "alert_p99": 60.0,
    },
    "aircraft_core_supplier_rating_duration_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Supplier quality rating calculation duration",
        "unit": "seconds",
        "alert_p99": 5.0,
    },
    "aircraft_core_material_trace_duration_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Material lot traceability query duration",
        "unit": "seconds",
        "alert_p99": 3.0,
    },
    "physics_twin_shop_floor_collection_latency_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Shop floor data collection latency",
        "unit": "seconds",
        "alert_p99": 0.5,
    },
    "aircraft_core_dashboard_update_latency_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "Real-time dashboard update latency",
        "unit": "seconds",
        "alert_p99": 5.0,
    },
    "physics_twin_uq_inference_duration_seconds": {
        "type": MetricType.HISTOGRAM,
        "description": "UQ inference duration",
        "unit": "seconds",
        "alert_p99": 0.01,
    },
    "physics_twin_mdo_7d_generation_progress": {
        "type": MetricType.GAUGE,
        "description": "7-discipline MDO generation progress",
        "unit": "percentage",
        "alert_no_convergence_min": 120.0,
    },
    "aircraft_core_traceability_coverage_percentage": {
        "type": MetricType.GAUGE,
        "description": "Requirements traceability coverage percentage",
        "unit": "percentage",
    },
}


class ObservabilityMetricsService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._samples: dict[str, list[MetricSample]] = {
            name: [] for name in METRIC_DEFINITIONS
        }
        self._summaries: dict[str, MetricSummary] = {
            name: MetricSummary(metric_name=name) for name in METRIC_DEFINITIONS
        }

    def recordDuration(
        self, metric_name: str, duration_seconds: float, labels: dict | None = None
    ) -> Optional[MetricSample]:
        if metric_name not in METRIC_DEFINITIONS:
            return None

        defn = METRIC_DEFINITIONS[metric_name]
        if defn["type"] not in (MetricType.HISTOGRAM, MetricType.GAUGE):
            return None

        sample = MetricSample(
            metric_name=metric_name,
            metric_type=defn["type"],
            value=duration_seconds,
            labels=labels or {},
        )
        self._samples[metric_name].append(sample)
        self._update_summary(metric_name, duration_seconds)
        return sample

    def recordGauge(
        self, metric_name: str, value: float, labels: dict | None = None
    ) -> Optional[MetricSample]:
        if metric_name not in METRIC_DEFINITIONS:
            return None

        defn = METRIC_DEFINITIONS[metric_name]
        if defn["type"] != MetricType.GAUGE:
            return None

        sample = MetricSample(
            metric_name=metric_name,
            metric_type=MetricType.GAUGE,
            value=value,
            labels=labels or {},
        )
        self._samples[metric_name].append(sample)
        self._summaries[metric_name].count += 1
        self._summaries[metric_name].sum += value
        self._summaries[metric_name].max = max(self._summaries[metric_name].max, value)
        self._summaries[metric_name].min = min(self._summaries[metric_name].min, value)
        return sample

    def _update_summary(self, metric_name: str, value: float) -> None:
        summary = self._summaries[metric_name]
        summary.count += 1
        summary.sum += value
        summary.min = min(summary.min, value)
        summary.max = max(summary.max, value)

        if summary.count > 0:
            sorted_vals = sorted(s.value for s in self._samples[metric_name])
            n = len(sorted_vals)
            summary.p50 = sorted_vals[int(n * 0.50)] if n > 0 else 0
            summary.p95 = sorted_vals[int(n * 0.95)] if n > 0 else 0
            summary.p99 = sorted_vals[int(n * 0.99)] if n > 0 else 0

    def getMetricSummary(self, metric_name: str) -> Optional[MetricSummary]:
        return self._summaries.get(metric_name)

    def getAllSummaries(self) -> list[MetricSummary]:
        return list(self._summaries.values())

    def checkAlerts(self) -> list[dict]:
        alerts = []
        for name, defn in METRIC_DEFINITIONS.items():
            summary = self._summaries[name]
            if summary.count == 0:
                continue

            alert_p99 = defn.get("alert_p99")
            if alert_p99 and summary.p99 > alert_p99:
                alerts.append({
                    "metric_name": name,
                    "alert_type": "P99ThresholdExceeded",
                    "current_p99": summary.p99,
                    "threshold": alert_p99,
                    "severity": "Warning",
                })

        return alerts

    def exportPrometheusFormat(self) -> str:
        lines = []
        for name, defn in METRIC_DEFINITIONS.items():
            lines.append(f"# HELP {name} {defn['description']}")
            lines.append(f"# TYPE {name} {defn['type'].value}")
            summary = self._summaries[name]
            if defn["type"] == MetricType.HISTOGRAM:
                lines.append(f'{name}_count {summary.count}')
                lines.append(f'{name}_sum {summary.sum}')
                if summary.count > 0:
                    lines.append(f'{name}_p50 {summary.p50}')
                    lines.append(f'{name}_p95 {summary.p95}')
                    lines.append(f'{name}_p99 {summary.p99}')
            elif defn["type"] == MetricType.GAUGE:
                if summary.count > 0:
                    lines.append(f'{name} {summary.max}')
            lines.append("")
        return "\n".join(lines)