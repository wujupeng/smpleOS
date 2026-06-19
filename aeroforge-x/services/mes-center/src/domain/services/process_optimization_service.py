from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.process_optimization import (
    BottleneckInfo,
    ImprovementMetrics,
    OptimizationType,
    OptimizationStatus,
    ProcessOptimization,
    ProcessParameter,
    SimulationResult,
    ValidationResult,
    ValidationStatus,
)

_STATIONS = [
    ("ST-001", "Forging Press A"),
    ("ST-002", "Forging Press B"),
    ("ST-003", "Heat Treatment Furnace"),
    ("ST-004", "CNC Machining Center"),
    ("ST-005", "Surface Treatment"),
    ("ST-006", "Inspection Station"),
    ("ST-007", "Assembly Station"),
    ("ST-008", "Final QC"),
]

_PROCESS_PARAMS = [
    ("forging_temperature", 1150.0, "°C", 900.0, 1300.0),
    ("press_speed", 50.0, "mm/s", 10.0, 120.0),
    ("holding_time", 30.0, "min", 5.0, 120.0),
    ("cooling_rate", 5.0, "°C/min", 1.0, 20.0),
    ("die_temperature", 350.0, "°C", 200.0, 500.0),
    ("lubrication_amount", 2.5, "ml/cm²", 0.5, 5.0),
]


class ProcessOptimizationService:
    def __init__(self) -> None:
        self._optimizations: dict[str, ProcessOptimization] = {}

    def analyze_process_bottleneck(
        self,
        tenant_id: str,
        project_id: str,
        process_route_id: str,
    ) -> ProcessOptimization:
        optimization = ProcessOptimization(
            tenant_id=tenant_id,
            project_id=project_id,
            process_route_id=process_route_id,
            optimization_type=OptimizationType.CYCLE_TIME,
        )

        bottlenecks: list[BottleneckInfo] = []
        for i, (sid, sname) in enumerate(_STATIONS):
            util = random.uniform(0.5, 0.98)
            wait = random.uniform(0, 120)
            process_time = random.uniform(10, 90)
            is_critical = i < 4
            severity = "high" if util > 0.9 else ("medium" if util > 0.75 else "low")

            bottlenecks.append(BottleneckInfo(
                station_id=sid,
                station_name=sname,
                utilization_rate=util,
                avg_wait_time_minutes=wait,
                avg_process_time_minutes=process_time,
                is_critical_path=is_critical,
                bottleneck_severity=severity,
            ))

        bottlenecks.sort(key=lambda b: b.utilization_rate, reverse=True)
        optimization.set_bottleneck_analysis(bottlenecks)
        optimization.status = OptimizationStatus.RUNNING

        self._optimizations[optimization.id] = optimization
        return optimization

    def optimize_process_parameters(
        self,
        optimization_id: str,
        optimization_type: OptimizationType = OptimizationType.QUALITY,
    ) -> ProcessOptimization | None:
        optimization = self._optimizations.get(optimization_id)
        if not optimization:
            return None

        optimization.optimization_type = optimization_type

        current_params: list[ProcessParameter] = []
        optimized_params: list[ProcessParameter] = []

        for name, default_val, unit, min_b, max_b in _PROCESS_PARAMS:
            current_val = default_val * random.uniform(0.85, 1.15)
            current_params.append(ProcessParameter(
                name=name, value=round(current_val, 2), unit=unit,
                min_bound=min_b, max_bound=max_b,
            ))

            improvement_dir = random.choice([-1, 1])
            optimized_val = current_val * (1 + improvement_dir * random.uniform(0.03, 0.12))
            optimized_val = min(max(optimized_val, min_b), max_b)
            optimized_params.append(ProcessParameter(
                name=name, value=round(optimized_val, 2), unit=unit,
                min_bound=min_b, max_bound=max_b,
            ))

        optimization.set_current_params(current_params)
        optimization.set_optimized_params(optimized_params)

        metrics = ImprovementMetrics(
            time_reduction_pct=random.uniform(5, 20),
            quality_improvement_pct=random.uniform(3, 15),
            cost_reduction_pct=random.uniform(2, 12),
            energy_reduction_pct=random.uniform(1, 8),
        )
        optimization.set_improvement_metrics(metrics)
        optimization.status = OptimizationStatus.COMPLETED

        return optimization

    def simulate_process_change(
        self, optimization_id: str
    ) -> ProcessOptimization | None:
        optimization = self._optimizations.get(optimization_id)
        if not optimization:
            return None

        result = SimulationResult(
            schedule_impact={
                "affected_orders": random.randint(2, 15),
                "reschedule_needed": True,
                "estimated_downtime_hours": round(random.uniform(0.5, 4.0), 1),
            },
            capacity_change_pct=round(random.uniform(-5, 15), 2),
            delivery_impact_days=round(random.uniform(-2, 3), 1),
            risk_assessment=random.choice(["low", "medium", "high"]),
            feasible=random.random() > 0.15,
        )
        optimization.set_simulation_result(result)
        return optimization

    def validate_process_optimization(
        self,
        optimization_id: str,
        sample_size: int = 30,
    ) -> ProcessOptimization | None:
        optimization = self._optimizations.get(optimization_id)
        if not optimization:
            return None

        pass_rate_before = random.uniform(0.82, 0.92)
        pass_rate_after = min(pass_rate_before + random.uniform(0.02, 0.12), 0.99)
        significance = random.uniform(0.01, 0.08)
        is_significant = significance < 0.05

        result = ValidationResult(
            sample_size=sample_size,
            pass_rate_before=pass_rate_before,
            pass_rate_after=pass_rate_after,
            statistical_significance=significance,
            is_significant=is_significant,
            validated_at=datetime.now(timezone.utc),
        )
        optimization.set_validation_result(result)
        return optimization

    def deploy_optimized_process(
        self, optimization_id: str
    ) -> ProcessOptimization | None:
        optimization = self._optimizations.get(optimization_id)
        if not optimization:
            return None

        if optimization.validation_status != ValidationStatus.VALIDATED:
            return None

        optimization.mark_deployed()
        return optimization

    def get_optimization(self, optimization_id: str) -> ProcessOptimization | None:
        return self._optimizations.get(optimization_id)