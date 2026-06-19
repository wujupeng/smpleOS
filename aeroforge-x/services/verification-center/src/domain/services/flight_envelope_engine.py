from __future__ import annotations

import math
from typing import Any

from src.domain.entities.flight_envelope_analysis import (
    FlightEnvelopeAnalysis,
    LimitSpeeds,
    LimitLoadFactors,
    VnDiagramPoint,
    EnvelopeViolation,
)


class FlightEnvelopeEngine:
    def compute_limit_speeds(self, config: dict[str, Any]) -> LimitSpeeds:
        mtow_kg = float(config.get("mtow_kg", 25))
        wing_area = float(config.get("wing_area_m2", 0.5))
        cl_max = float(config.get("cl_max", 1.5))
        cl_max_flap = float(config.get("cl_max_flap", 2.0))
        cruise_speed_kmh = float(config.get("cruise_speed_kmh", 100))
        v_cruise = cruise_speed_kmh / 3.6
        wing_loading = (mtow_kg * 9.81) / wing_area if wing_area > 0 else 100

        rho = 1.225
        vs1 = math.sqrt(2 * wing_loading / (rho * cl_max)) if rho * cl_max > 0 else 10
        vs0 = math.sqrt(2 * wing_loading / (rho * cl_max_flap)) if rho * cl_max_flap > 0 else 8
        va = vs1 * math.sqrt(3.5)
        vc = v_cruise if v_cruise > 0 else va * 1.2
        vd = vc * 1.25
        vne = vd * 0.9

        return LimitSpeeds(
            vs1_ms=round(vs1, 2),
            vs0_ms=round(vs0, 2),
            va_ms=round(va, 2),
            vc_ms=round(vc, 2),
            vd_ms=round(vd, 2),
            vne_ms=round(vne, 2),
        )

    def compute_limit_load_factors(self, config: dict[str, Any]) -> LimitLoadFactors:
        mtow_kg = float(config.get("mtow_kg", 25))
        if mtow_kg <= 500:
            n_max_pos = min(3.8, 2.1 + 24000 / (mtow_kg + 10000))
        else:
            n_max_pos = 2.5
        n_max_neg = -1.0 if mtow_kg > 500 else -0.4 * n_max_pos
        return LimitLoadFactors(
            n_max_positive=round(n_max_pos, 2),
            n_max_negative=round(n_max_neg, 2),
            n_ultimate_positive=round(n_max_pos * 1.5, 2),
            n_ultimate_negative=round(n_max_neg * 1.5, 2),
        )

    def generate_vn_diagram(self, limit_speeds: LimitSpeeds, limit_loads: LimitLoadFactors) -> list[VnDiagramPoint]:
        points: list[VnDiagramPoint] = []
        points.append(VnDiagramPoint(speed_ms=0, load_factor=0, label="origin"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.vs1, load_factor=1.0, label="VS1@1g"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.va, load_factor=limit_loads.n_max_positive, label="VA@n_max"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.vc, load_factor=limit_loads.n_max_positive, label="VC@n_max"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.vc, load_factor=limit_loads.n_max_negative, label="VC@n_min"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.vd, load_factor=0, label="VD@0g"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.vd, load_factor=limit_loads.n_max_negative * 0.5, label="VD@n_min"))
        points.append(VnDiagramPoint(speed_ms=limit_speeds.vs1, load_factor=limit_loads.n_max_negative, label="VS1@n_min"))
        return points

    def overlay_gust_envelope(self, limit_speeds: LimitSpeeds, config: dict[str, Any]) -> list[VnDiagramPoint]:
        wing_loading = float(config.get("wing_kg_m2", 50))
        mu_g = 2 * wing_loading / (1.225 * 0.1 * 9.81 * 0.08) if wing_loading > 0 else 20
        kg = 0.88 * mu_g / (5.3 + mu_g) if mu_g > 0 else 0.8

        u_g_cruise = 15.24 * kg
        u_g_dive = 7.62 * kg

        gust_points: list[VnDiagramPoint] = []
        gust_points.append(VnDiagramPoint(speed_ms=limit_speeds.vc, load_factor=1 + u_g_cruise * 0.1, label="gust_VC_pos"))
        gust_points.append(VnDiagramPoint(speed_ms=limit_speeds.vd, load_factor=1 + u_g_dive * 0.1, label="gust_VD_pos"))
        gust_points.append(VnDiagramPoint(speed_ms=limit_speeds.vc, load_factor=1 - u_g_cruise * 0.08, label="gust_VC_neg"))
        gust_points.append(VnDiagramPoint(speed_ms=limit_speeds.vd, load_factor=1 - u_g_dive * 0.08, label="gust_VD_neg"))
        return gust_points

    def detect_envelope_violations(
        self, vn_diagram: list[VnDiagramPoint], gust_envelope: list[VnDiagramPoint],
        limit_speeds: LimitSpeeds, limit_loads: LimitLoadFactors,
    ) -> list[EnvelopeViolation]:
        violations: list[EnvelopeViolation] = []
        for point in vn_diagram + gust_envelope:
            if point.speed_ms > limit_speeds.vne_ms:
                violations.append(EnvelopeViolation(
                    violation_type="speed_exceeded",
                    speed_ms=point.speed_ms,
                    load_factor=point.load_factor,
                    description=f"Speed {point.speed_ms:.1f} m/s exceeds VNE {limit_speeds.vne_ms:.1f} m/s",
                    severity="critical",
                ))
            if point.load_factor > limit_loads.n_max_positive:
                violations.append(EnvelopeViolation(
                    violation_type="load_exceeded_positive",
                    speed_ms=point.speed_ms,
                    load_factor=point.load_factor,
                    description=f"Load factor {point.load_factor:.2f} exceeds positive limit {limit_loads.n_max_positive:.2f}",
                    severity="critical",
                ))
            if point.load_factor < limit_loads.n_max_negative:
                violations.append(EnvelopeViolation(
                    violation_type="load_exceeded_negative",
                    speed_ms=point.speed_ms,
                    load_factor=point.load_factor,
                    description=f"Load factor {point.load_factor:.2f} below negative limit {limit_loads.n_max_negative:.2f}",
                    severity="warning",
                ))
        return violations

    def run_full_analysis(self, config: dict[str, Any]) -> FlightEnvelopeAnalysis:
        analysis = FlightEnvelopeAnalysis(aircraft_config=config, status="running")
        analysis.limit_speeds = self.compute_limit_speeds(config)
        analysis.limit_load_factors = self.compute_limit_load_factors(config)
        analysis.vn_diagram = self.generate_vn_diagram(analysis.limit_speeds, analysis.limit_load_factors)
        analysis.gust_envelope = self.overlay_gust_envelope(analysis.limit_speeds, config)
        analysis.violations = self.detect_envelope_violations(
            analysis.vn_diagram, analysis.gust_envelope,
            analysis.limit_speeds, analysis.limit_load_factors,
        )
        analysis.complete()
        return analysis