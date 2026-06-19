from __future__ import annotations

import math
from typing import Any

from src.domain.entities.stability_analysis import (
    StabilityAnalysis,
    StabilityResult,
    ParameterSuggestion,
)


class StabilityEngine:
    def analyze_longitudinal_stability(self, config: dict[str, Any]) -> StabilityResult:
        wing_area = float(config.get("wing_area_m2", 1.0))
        wing_span = float(config.get("wing_span_m", 2.0))
        wing_chord = wing_area / wing_span if wing_span > 0 else 0.3
        h_tail_area = float(config.get("h_tail_area_m2", 0.05))
        h_tail_arm = float(config.get("h_tail_arm_m", 0.6))
        cg_position = float(config.get("cg_position_pct_mac", 25.0))
        ac_position = float(config.get("ac_position_pct_mac", 25.0))

        tail_volume = (h_tail_area * h_tail_arm) / (wing_area * wing_chord) if wing_area * wing_chord > 0 else 0
        neutral_point = ac_position + tail_volume * 0.6
        static_margin = neutral_point - cg_position

        cl_alpha = 2 * math.pi
        cm_alpha = -cl_alpha * (static_margin / 100.0) if static_margin > 0 else cl_alpha * abs(static_margin) / 100.0

        is_stable = static_margin > 5.0

        return StabilityResult(
            static_margin_pct_mac=round(static_margin, 2),
            neutral_point_pct_mac=round(neutral_point, 2),
            pitch_stiffness_derivative=round(cm_alpha, 4),
            is_longitudinally_stable=is_stable,
        )

    def analyze_lateral_stability(self, config: dict[str, Any]) -> StabilityResult:
        wing_dihedral = float(config.get("dihedral_angle_deg", 3.0))
        sweep_angle = float(config.get("sweep_angle_deg", 2.0))
        wing_span = float(config.get("wing_span_m", 2.0))
        v_tail_area = float(config.get("v_tail_area_m2", 0.03))
        h_tail_arm = float(config.get("h_tail_arm_m", 0.6))
        wing_area = float(config.get("wing_area_m2", 1.0))

        cl_beta_dihedral = -0.0002 * wing_dihedral * 57.3
        cl_beta_sweep = -0.0001 * abs(sweep_angle) * 57.3
        cl_beta_total = cl_beta_dihedral + cl_beta_sweep

        vt_volume = (v_tail_area * h_tail_arm) / (wing_area * wing_span) if wing_area * wing_span > 0 else 0
        cn_beta = vt_volume * 0.02

        zeta_d = 0.08 + 0.02 * abs(cl_beta_total)
        omega_d = 2.0 + 1.5 * vt_volume

        is_stable = cl_beta_total < 0 and zeta_d > 0.02

        return StabilityResult(
            roll_stiffness_derivative=round(cl_beta_total, 4),
            dutch_roll_damping_ratio=round(zeta_d, 4),
            dutch_roll_frequency_hz=round(omega_d / (2 * math.pi), 4),
            is_laterally_stable=is_stable,
        )

    def analyze_directional_stability(self, config: dict[str, Any]) -> StabilityResult:
        v_tail_area = float(config.get("v_tail_area_m2", 0.03))
        h_tail_arm = float(config.get("h_tail_arm_m", 0.6))
        wing_area = float(config.get("wing_area_m2", 1.0))
        wing_span = float(config.get("wing_span_m", 2.0))

        vt_volume = (v_tail_area * h_tail_arm) / (wing_area * wing_span) if wing_area * wing_span > 0 else 0
        cn_beta = vt_volume * 0.02
        weathercock = cn_beta * 57.3

        is_stable = cn_beta > 0

        return StabilityResult(
            yaw_stiffness_derivative=round(cn_beta, 4),
            weathercock_stability=round(weathercock, 4),
            is_directionally_stable=is_stable,
        )

    def suggest_parameter_adjustments(self, analysis: StabilityAnalysis) -> list[ParameterSuggestion]:
        suggestions: list[ParameterSuggestion] = []
        if not analysis.longitudinal_result.is_longitudinally_stable:
            sm = analysis.longitudinal_result.static_margin_pct_mac
            if sm < 5.0:
                suggestions.append(ParameterSuggestion(
                    parameter="cg_position_pct_mac",
                    current_value=float(analysis.aircraft_config.get("cg_position_pct_mac", 25)),
                    suggested_value=max(10, 25 - (5 - sm)),
                    reason=f"Move CG forward to increase static margin from {sm:.1f}% to >5%",
                ))
                suggestions.append(ParameterSuggestion(
                    parameter="h_tail_area_m2",
                    current_value=float(analysis.aircraft_config.get("h_tail_area_m2", 0.05)),
                    suggested_value=float(analysis.aircraft_config.get("h_tail_area_m2", 0.05)) * 1.3,
                    reason="Increase horizontal tail area to improve longitudinal stability",
                ))
        if not analysis.lateral_result.is_laterally_stable:
            suggestions.append(ParameterSuggestion(
                parameter="dihedral_angle_deg",
                current_value=float(analysis.aircraft_config.get("dihedral_angle_deg", 3)),
                suggested_value=float(analysis.aircraft_config.get("dihedral_angle_deg", 3)) + 2,
                reason="Increase dihedral angle to improve lateral stability",
            ))
        if not analysis.directional_result.is_directionally_stable:
            suggestions.append(ParameterSuggestion(
                parameter="v_tail_area_m2",
                current_value=float(analysis.aircraft_config.get("v_tail_area_m2", 0.03)),
                suggested_value=float(analysis.aircraft_config.get("v_tail_area_m2", 0.03)) * 1.4,
                reason="Increase vertical tail area to improve directional stability",
            ))
        return suggestions

    def run_full_analysis(self, config: dict[str, Any]) -> StabilityAnalysis:
        analysis = StabilityAnalysis(aircraft_config=config, status="running")
        analysis.longitudinal_result = self.analyze_longitudinal_stability(config)
        analysis.lateral_result = self.analyze_lateral_stability(config)
        analysis.directional_result = self.analyze_directional_stability(config)
        analysis.suggestions = self.suggest_parameter_adjustments(analysis)
        analysis.complete()
        return analysis