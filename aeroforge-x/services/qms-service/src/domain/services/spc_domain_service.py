from __future__ import annotations

import logging
import math
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.spc_control_chart import (
    SPCControlChart, ChartType, ChartStatus,
    SpecificationLimits, ControlLimits, OutOfControlRule, DEFAULT_OOC_RULES,
)
from .entities.spc_measurement import SPCMeasurement

logger = logging.getLogger(__name__)


class ProcessCapability:
    def __init__(self, cp: float, cpk: float, pp: float, ppk: float) -> None:
        self.cp = round(cp, 4)
        self.cpk = round(cpk, 4)
        self.pp = round(pp, 4)
        self.ppk = round(ppk, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cp": self.cp,
            "cpk": self.cpk,
            "pp": self.pp,
            "ppk": self.ppk,
            "grade": self.grade,
        }

    @property
    def grade(self) -> str:
        min_idx = min(self.cp, self.cpk)
        if min_idx >= 1.67:
            return "A (优秀)"
        elif min_idx >= 1.33:
            return "B (良好)"
        elif min_idx >= 1.0:
            return "C (勉强)"
        else:
            return "D (不足)"


class SPCDomainService:
    def __init__(self) -> None:
        self._charts: dict[str, SPCControlChart] = {}
        self._measurements: dict[str, list[SPCMeasurement]] = {}

    def create_control_chart(
        self,
        tenant_id: str,
        project_id: str,
        chart_type: ChartType,
        process_name: str,
        characteristic_name: str,
        specification_limits: SpecificationLimits,
        sample_size: int = 5,
        sampling_frequency: str = "per_lot",
        created_by: str = "",
    ) -> SPCControlChart:
        chart = SPCControlChart(
            tenant_id=tenant_id,
            project_id=project_id,
            chart_type=chart_type,
            process_name=process_name,
            characteristic_name=characteristic_name,
            specification_limits=specification_limits,
            sample_size=sample_size,
            sampling_frequency=sampling_frequency,
            created_by=created_by,
        )

        self._charts[chart.id] = chart
        self._measurements[chart.id] = []

        chart.add_domain_event(DomainEvent(
            event_type="spc.chart_created",
            aggregate_id=chart.id,
            payload={"chart_id": chart.id, "process_name": process_name},
        ))

        logger.info("Created SPC control chart %s for %s", chart.id, process_name)
        return chart

    def calculate_control_limits(self, chart_id: str) -> SPCControlChart | None:
        chart = self._charts.get(chart_id)
        if chart is None:
            return None

        measurements = self._measurements.get(chart_id, [])
        if len(measurements) < 2:
            return chart

        means = [m.mean for m in measurements]
        ranges = [m.range_val for m in measurements]

        cl = sum(means) / len(means)
        avg_range = sum(ranges) / len(ranges) if ranges else 0.0

        n = chart.sample_size
        A2 = self._get_A2(n)
        D3 = self._get_D3(n)
        D4 = self._get_D4(n)

        ucl = cl + A2 * avg_range
        lcl = cl - A2 * avg_range

        chart.set_control_limits(ucl=round(ucl, 6), lcl=round(lcl, 6), cl=round(cl, 6))

        return chart

    def add_measurement(
        self,
        chart_id: str,
        sample_group: int,
        measurement_values: list[float],
        measured_by: str = "",
    ) -> SPCMeasurement | None:
        chart = self._charts.get(chart_id)
        if chart is None:
            return None

        measurement = SPCMeasurement(
            chart_id=chart_id,
            sample_group=sample_group,
            measurement_values=measurement_values,
            measured_by=measured_by,
        )
        measurement.compute_statistics()

        violations = self._detect_out_of_control(chart, measurement)
        measurement.is_out_of_control = len(violations) > 0
        measurement.violation_rules = violations

        self._measurements[chart_id].append(measurement)

        if measurement.is_out_of_control:
            chart.add_domain_event(DomainEvent(
                event_type="spc.out_of_control",
                aggregate_id=chart_id,
                payload={
                    "measurement_id": measurement.id,
                    "sample_group": sample_group,
                    "violations": violations,
                },
            ))
            logger.warning("Out of control detected: chart=%s, group=%d, rules=%s",
                           chart_id, sample_group, violations)

        return measurement

    def detect_out_of_control(self, chart_id: str) -> list[SPCMeasurement]:
        chart = self._charts.get(chart_id)
        if chart is None:
            return []

        measurements = self._measurements.get(chart_id, [])
        ooc_measurements = []

        for m in measurements:
            violations = self._detect_out_of_control(chart, m)
            m.is_out_of_control = len(violations) > 0
            m.violation_rules = violations
            if m.is_out_of_control:
                ooc_measurements.append(m)

        return ooc_measurements

    def calculate_process_capability(self, chart_id: str) -> ProcessCapability | None:
        chart = self._charts.get(chart_id)
        if chart is None:
            return None

        measurements = self._measurements.get(chart_id, [])
        if len(measurements) < 2:
            return None

        means = [m.mean for m in measurements]
        all_values = []
        for m in measurements:
            all_values.extend(m.measurement_values)

        if not all_values:
            return None

        grand_mean = sum(means) / len(means)
        n = len(all_values)
        within_std = 0.0
        if len(measurements) > 1:
            within_var = sum((m.mean - grand_mean) ** 2 for m in measurements) / (len(measurements) - 1)
            avg_range = sum(m.range_val for m in measurements) / len(measurements)
            d2 = self._get_d2(chart.sample_size)
            within_std = avg_range / d2 if d2 > 0 else (within_var ** 0.5)

        overall_var = sum((x - grand_mean) ** 2 for x in all_values) / (n - 1) if n > 1 else 0
        overall_std = overall_var ** 0.5

        usl = chart.specification_limits.usl
        lsl = chart.specification_limits.lsl

        if within_std <= 0 or overall_std <= 0:
            return ProcessCapability(cp=0, cpk=0, pp=0, ppk=0)

        cp = (usl - lsl) / (6 * within_std)
        cpk = min((usl - grand_mean) / (3 * within_std), (grand_mean - lsl) / (3 * within_std))
        pp = (usl - lsl) / (6 * overall_std)
        ppk = min((usl - grand_mean) / (3 * overall_std), (grand_mean - lsl) / (3 * overall_std))

        return ProcessCapability(cp=cp, cpk=cpk, pp=pp, ppk=ppk)

    def generate_spc_report(self, chart_id: str) -> dict[str, Any] | None:
        chart = self._charts.get(chart_id)
        if chart is None:
            return None

        measurements = self._measurements.get(chart_id, [])
        ooc_count = sum(1 for m in measurements if m.is_out_of_control)
        capability = self.calculate_process_capability(chart_id)

        return {
            "chart": chart.to_dict(),
            "total_samples": len(measurements),
            "out_of_control_count": ooc_count,
            "process_capability": capability.to_dict() if capability else None,
            "recent_measurements": [m.to_dict() for m in measurements[-20:]],
        }

    def get_chart(self, chart_id: str) -> SPCControlChart | None:
        return self._charts.get(chart_id)

    def get_measurements(self, chart_id: str) -> list[SPCMeasurement]:
        return self._measurements.get(chart_id, [])

    def list_charts(
        self,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> list[SPCControlChart]:
        charts = list(self._charts.values())
        if tenant_id:
            charts = [c for c in charts if c.tenant_id == tenant_id]
        if project_id:
            charts = [c for c in charts if c.project_id == project_id]
        return charts

    def _detect_out_of_control(self, chart: SPCControlChart, measurement: SPCMeasurement) -> list[int]:
        violations: list[int] = []
        measurements = self._measurements.get(chart.id, [])
        idx = next((i for i, m in enumerate(measurements) if m.id == measurement.id), -1)
        if idx == -1:
            idx = len(measurements)

        all_means = [m.mean for m in measurements[:idx]] + [measurement.mean]
        cl = chart.control_limits.cl
        ucl = chart.control_limits.ucl
        lcl = chart.control_limits.lcl

        if cl == 0 and ucl == 0 and lcl == 0:
            return violations

        sigma = (ucl - cl) / 3 if ucl != cl else 1.0

        for rule in chart.out_of_control_rules:
            if not rule.enabled:
                continue

            if rule.rule_id == 1:
                if measurement.mean > ucl or measurement.mean < lcl:
                    violations.append(1)

            elif rule.rule_id == 2:
                if len(all_means) >= 9:
                    last_9 = all_means[-9:]
                    if all(m > cl for m in last_9) or all(m < cl for m in last_9):
                        violations.append(2)

            elif rule.rule_id == 3:
                if len(all_means) >= 6:
                    last_6 = all_means[-6:]
                    if all(last_6[i] < last_6[i + 1] for i in range(5)) or \
                       all(last_6[i] > last_6[i + 1] for i in range(5)):
                        violations.append(3)

            elif rule.rule_id == 4:
                if len(all_means) >= 14:
                    last_14 = all_means[-14:]
                    alternating = True
                    for i in range(1, 13):
                        if not ((last_14[i] - last_14[i - 1]) * (last_14[i + 1] - last_14[i]) < 0):
                            alternating = False
                            break
                    if alternating:
                        violations.append(4)

            elif rule.rule_id == 5:
                if len(all_means) >= 3 and sigma > 0:
                    last_3 = all_means[-3:]
                    count_beyond_2sigma = sum(
                        1 for m in last_3 if m > cl + 2 * sigma or m < cl - 2 * sigma
                    )
                    if count_beyond_2sigma >= 2:
                        violations.append(5)

            elif rule.rule_id == 6:
                if len(all_means) >= 5 and sigma > 0:
                    last_5 = all_means[-5:]
                    count_beyond_1sigma = sum(
                        1 for m in last_5 if m > cl + sigma or m < cl - sigma
                    )
                    if count_beyond_1sigma >= 4:
                        violations.append(6)

            elif rule.rule_id == 7:
                if len(all_means) >= 15 and sigma > 0:
                    last_15 = all_means[-15:]
                    all_within_1sigma = all(
                        cl - sigma <= m <= cl + sigma for m in last_15
                    )
                    if all_within_1sigma:
                        violations.append(7)

            elif rule.rule_id == 8:
                if len(all_means) >= 8 and sigma > 0:
                    last_8 = all_means[-8:]
                    all_beyond_1sigma = all(
                        m > cl + sigma or m < cl - sigma for m in last_8
                    )
                    all_within_3sigma = all(
                        cl - 3 * sigma <= m <= cl + 3 * sigma for m in last_8
                    )
                    if all_beyond_1sigma and all_within_3sigma:
                        violations.append(8)

        return violations

    def _get_A2(self, n: int) -> float:
        table = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483,
                 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
        return table.get(n, 0.308)

    def _get_D3(self, n: int) -> float:
        table = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
        return table.get(n, 0.223)

    def _get_D4(self, n: int) -> float:
        table = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004,
                 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}
        return table.get(n, 1.777)

    def _get_d2(self, n: int) -> float:
        table = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534,
                 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
        return table.get(n, 3.078)