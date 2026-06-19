from __future__ import annotations

import math
from typing import Any

from .entities.fenics_advanced import (
    CustomFEATask, UFLDefinition, FEASolutionField, CustomFEAStatus,
    FatigueAnalysisTask, RainflowCycle, FatigueDamageResult, MeanStressCorrection,
    BucklingAnalysisTask, BucklingMode,
)


class FEniCSAdvancedService:

    def submit_custom_fea(
        self,
        model_id: str,
        project_id: str,
        tenant_id: str,
        ufl_filename: str,
        ufl_content: str,
        boundary_conditions: list[dict[str, Any]] | None = None,
        material_props: dict[str, float] | None = None,
    ) -> CustomFEATask:
        ufl = UFLDefinition(
            filename=ufl_filename,
            content=ufl_content,
            boundary_conditions=boundary_conditions or [],
            material_props=material_props or {},
        )
        task = CustomFEATask(
            model_id=model_id,
            project_id=project_id,
            tenant_id=tenant_id,
            ufl_definition=ufl,
        )

        task.status = CustomFEAStatus.PARSING_UFL
        task.status = CustomFEAStatus.SOLVING

        fields = self._solve_custom_fea(ufl)
        task.complete(fields, solve_time=1.5)
        return task

    def _solve_custom_fea(self, ufl: UFLDefinition) -> list[FEASolutionField]:
        displacement = FEASolutionField(
            name="displacement",
            values=[0.001 * i for i in range(100)],
            min_val=0.0,
            max_val=0.099,
        )
        stress = FEASolutionField(
            name="von_mises_stress",
            values=[100 + 10 * i for i in range(100)],
            min_val=100.0,
            max_val=1090.0,
        )
        return [displacement, stress]

    def run_fatigue_analysis(
        self,
        model_id: str,
        project_id: str,
        tenant_id: str,
        load_spectrum: list[float],
        sn_curve: list[dict[str, float]] | None = None,
        mean_stress_correction: MeanStressCorrection = MeanStressCorrection.GOODMAN,
        endurance_limit: float = 1e7,
    ) -> FatigueAnalysisTask:
        task = FatigueAnalysisTask(
            model_id=model_id,
            project_id=project_id,
            tenant_id=tenant_id,
            load_spectrum=load_spectrum,
            sn_curve=sn_curve or self._default_sn_curve(),
            mean_stress_correction=mean_stress_correction,
            endurance_limit=endurance_limit,
        )

        task.status = FatigueAnalysisStatus.PROCESSING_SPECTRUM
        cycles = self._rainflow_counting(load_spectrum)

        task.status = FatigueAnalysisStatus.COMPUTING_DAMAGE
        damage_results = self._compute_fatigue_damage(
            cycles, task.sn_curve, mean_stress_correction, endurance_limit
        )

        task.complete(cycles, damage_results)
        return task

    def _default_sn_curve(self) -> list[dict[str, float]]:
        return [
            {"cycles": 1e3, "stress_amplitude": 800},
            {"cycles": 1e4, "stress_amplitude": 500},
            {"cycles": 1e5, "stress_amplitude": 300},
            {"cycles": 1e6, "stress_amplitude": 200},
            {"cycles": 1e7, "stress_amplitude": 150},
        ]

    def _rainflow_counting(self, spectrum: list[float]) -> list[RainflowCycle]:
        if len(spectrum) < 2:
            return []

        cycles: list[RainflowCycle] = []
        peaks = self._extract_peaks(spectrum)

        for i in range(0, len(peaks) - 1, 2):
            if i + 1 < len(peaks):
                range_val = abs(peaks[i + 1] - peaks[i])
                mean = (peaks[i] + peaks[i + 1]) / 2
                cycles.append(RainflowCycle(range_val=range_val, mean=mean))

        if not cycles and len(peaks) >= 2:
            range_val = abs(peaks[-1] - peaks[0])
            mean = (peaks[-1] + peaks[0]) / 2
            cycles.append(RainflowCycle(range_val=range_val, mean=mean))

        return cycles

    def _extract_peaks(self, data: list[float]) -> list[float]:
        if len(data) < 3:
            return list(data)

        peaks = [data[0]]
        for i in range(1, len(data) - 1):
            if (data[i] > data[i - 1] and data[i] > data[i + 1]) or \
               (data[i] < data[i - 1] and data[i] < data[i + 1]):
                peaks.append(data[i])
        peaks.append(data[-1])
        return peaks

    def _compute_fatigue_damage(
        self,
        cycles: list[RainflowCycle],
        sn_curve: list[dict[str, float]],
        correction: MeanStressCorrection,
        endurance_limit: float,
    ) -> list[FatigueDamageResult]:
        results = []
        total_damage = 0.0

        for elem_id in range(10):
            stress_factor = 0.8 + 0.04 * elem_id
            elem_damage = 0.0

            for cycle in cycles:
                amplitude = cycle.range_val / 2 * stress_factor
                mean_stress = abs(cycle.mean) * stress_factor

                if correction == MeanStressCorrection.GOODMAN:
                    corrected_amplitude = amplitude / (1 - mean_stress / 1000) if mean_stress < 1000 else amplitude
                elif correction == MeanStressCorrection.GERBER:
                    corrected_amplitude = amplitude / (1 - (mean_stress / 1000) ** 2) if mean_stress < 1000 else amplitude
                else:
                    corrected_amplitude = amplitude

                n_to_failure = self._interpolate_sn_curve(corrected_amplitude, sn_curve, endurance_limit)
                if n_to_failure > 0:
                    elem_damage += cycle.count / n_to_failure

            total_damage += elem_damage
            life_cycles = 1.0 / elem_damage if elem_damage > 0 else float("inf")
            results.append(FatigueDamageResult(
                element_id=elem_id,
                damage=round(elem_damage, 8),
                life_cycles=round(life_cycles, 2),
                critical=elem_damage > 0.5,
            ))

        return results

    def _interpolate_sn_curve(
        self, amplitude: float, sn_curve: list[dict[str, float]], endurance_limit: float
    ) -> float:
        if not sn_curve:
            return endurance_limit

        sorted_curve = sorted(sn_curve, key=lambda x: x["stress_amplitude"], reverse=True)

        if amplitude >= sorted_curve[0]["stress_amplitude"]:
            return sorted_curve[0]["cycles"]
        if amplitude <= sorted_curve[-1]["stress_amplitude"]:
            return endurance_limit

        for i in range(len(sorted_curve) - 1):
            s1 = sorted_curve[i]["stress_amplitude"]
            s2 = sorted_curve[i + 1]["stress_amplitude"]
            n1 = sorted_curve[i]["cycles"]
            n2 = sorted_curve[i + 1]["cycles"]

            if s2 <= amplitude <= s1:
                log_n = math.log10(n1) + (math.log10(n2) - math.log10(n1)) * \
                        (amplitude - s1) / (s2 - s1)
                return 10 ** log_n

        return endurance_limit

    def run_buckling_analysis(
        self,
        model_id: str,
        project_id: str,
        tenant_id: str,
        num_modes: int = 5,
    ) -> BucklingAnalysisTask:
        task = BucklingAnalysisTask(
            model_id=model_id,
            project_id=project_id,
            tenant_id=tenant_id,
            num_modes=num_modes,
        )

        task.status = BucklingAnalysisStatus.SOLVING

        modes = []
        for i in range(1, num_modes + 1):
            load_factor = 2.5 + i * 0.8 + 0.1 * math.sin(i)
            modes.append(BucklingMode(
                mode_number=i,
                critical_load_factor=round(load_factor, 4),
                description=f"Mode {i}: {'global' if i <= 2 else 'local'} buckling",
            ))

        task.complete(modes)
        return task