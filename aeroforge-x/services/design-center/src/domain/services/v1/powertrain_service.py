from __future__ import annotations

from typing import Any

from src.domain.entities.v1.powertrain_model import (
    PowertrainModel,
    MotorSpec,
    BatterySpec,
    ESCSpec,
    PowertrainStatus,
)


class PowertrainService:
    def generate_powertrain(self, spec_params: dict[str, Any]) -> PowertrainModel:
        mtow = float(spec_params.get("mtow_estimate_kg", 25.0))
        cruise_speed_kmh = float(spec_params.get("cruise_speed_kmh", 100))
        range_km = float(spec_params.get("range_km", 50))
        power_type = spec_params.get("power_type", "electric")
        motor_count = int(spec_params.get("motor_count", self._default_motor_count(spec_params)))

        if power_type == "electric":
            return self._generate_electric_powertrain(mtow, cruise_speed_kmh, range_km, motor_count, spec_params)
        return self._generate_hybrid_powertrain(mtow, cruise_speed_kmh, range_km, motor_count, spec_params)

    def _generate_electric_powertrain(
        self, mtow: float, cruise_speed_kmh: float, range_km: float, motor_count: int, spec_params: dict[str, Any]
    ) -> PowertrainModel:
        thrust_per_motor = (mtow * 9.81 * 0.5) / motor_count
        cruise_power_w = mtow * 9.81 * (cruise_speed_kmh / 3.6) * 0.08
        endurance_min = (range_km / cruise_speed_kmh) * 60 if cruise_speed_kmh > 0 else 30
        energy_wh = cruise_power_w * (endurance_min / 60.0) * 1.3
        battery_voltage = 22.2
        capacity_mah = (energy_wh / battery_voltage) * 1000
        max_current = cruise_power_w / battery_voltage
        esc_current = max_current * 1.5

        model = PowertrainModel(
            motor_spec=MotorSpec(
                motor_type="brushless_outrunner",
                max_thrust_n=round(thrust_per_motor, 1),
                kv_rating=600,
                weight_kg=round(thrust_per_motor * 0.01, 3),
                voltage_range=(14.8, 25.2),
                efficiency_pct=85.0,
            ),
            battery_spec=BatterySpec(
                chemistry="lipo",
                capacity_mah=round(capacity_mah, 0),
                cell_count=6,
                voltage_v=battery_voltage,
                max_discharge_c=round(esc_current / (capacity_mah / 1000), 1),
                weight_kg=round(energy_wh / 200, 3),
            ),
            esc_spec=ESCSpec(
                max_current_a=round(esc_current, 1),
                voltage_range=(14.8, 25.2),
                weight_kg=round(esc_current * 0.005, 3),
                protocol="dshot600",
            ),
            thrust_params={
                "motor_count": motor_count,
                "total_max_thrust_n": round(thrust_per_motor * motor_count, 1),
                "thrust_to_weight_ratio": round((thrust_per_motor * motor_count) / (mtow * 9.81), 3),
            },
            propeller_params={
                "diameter_inch": round(thrust_per_motor ** 0.33 * 1.5, 1),
                "pitch_inch": round(thrust_per_motor ** 0.33 * 1.0, 1),
                "blade_count": 2,
            },
        )
        model.mark_configured()
        return model

    def _generate_hybrid_powertrain(
        self, mtow: float, cruise_speed_kmh: float, range_km: float, motor_count: int, spec_params: dict[str, Any]
    ) -> PowertrainModel:
        model = self._generate_electric_powertrain(mtow, cruise_speed_kmh, range_km * 0.3, motor_count, spec_params)
        model.fuel_system = {
            "type": "range_extender",
            "fuel_type": "gasoline",
            "tank_capacity_l": round(range_km * mtow * 0.001, 1),
            "generator_power_w": round(mtow * 9.81 * (cruise_speed_kmh / 3.6) * 0.06, 0),
        }
        return model

    def _default_motor_count(self, spec_params: dict[str, Any]) -> int:
        aircraft_type = spec_params.get("aircraft_type", "fixed_wing")
        if aircraft_type == "evtol":
            return 8
        elif aircraft_type == "uav":
            return 4
        return 1