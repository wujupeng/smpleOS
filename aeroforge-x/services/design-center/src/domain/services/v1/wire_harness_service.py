from __future__ import annotations

from typing import Any

from src.domain.entities.v1.wire_harness_model import (
    WireHarnessModel,
    WireSpec,
    ConnectorSpec,
    HarnessType,
    HarnessStatus,
)


class WireHarnessService:
    def generate_wire_harness(self, spec_params: dict[str, Any], powertrain_params: dict[str, Any] | None = None) -> WireHarnessModel:
        motor_count = int(spec_params.get("motor_count", powertrain_params.get("motor_count", 1) if powertrain_params else 1))
        battery_voltage = float(powertrain_params.get("battery_voltage", 22.2) if powertrain_params else 22.2)
        max_current = float(powertrain_params.get("max_current_a", 30.0) if powertrain_params else 30.0)

        harness = WireHarnessModel(harness_type=HarnessType.PRIMARY)

        for i in range(motor_count):
            wire = WireSpec(
                wire_id=f"W-MOTOR-{i + 1:03d}",
                gauge_awg=self._select_wire_gauge(max_current / motor_count),
                conductor_material="copper",
                insulation_type="ptfe",
                length_m=round(0.3 + i * 0.15, 3),
                voltage_rating_v=600.0,
                current_capacity_a=round(max_current / motor_count, 1),
                color_code="red" if i % 2 == 0 else "black",
            )
            harness.add_wire(wire)

        signal_wires = self._generate_signal_wires(spec_params)
        for wire in signal_wires:
            harness.add_wire(wire)

        esc_connector = ConnectorSpec(
            connector_id="CN-ESC-001",
            connector_type="xt90",
            pin_count=2,
            manufacturer="XT",
            part_number="XT90-S",
        )
        harness.add_connector(esc_connector)

        if motor_count > 1:
            bus_connector = ConnectorSpec(
                connector_id="CN-BUS-001",
                connector_type="d_sub",
                pin_count=motor_count * 3,
                manufacturer="Molex",
                part_number=f"DSUB-{motor_count * 3}",
            )
            harness.add_connector(bus_connector)

        for wire in harness.wire_list:
            routing = {
                "wire_id": wire.wire_id,
                "start_point": {"x": 0.0, "y": 0.0, "z": 0.0},
                "end_point": {"x": wire.length_m, "y": 0.0, "z": 0.0},
                "length_m": wire.length_m,
                "bend_radius_m": 0.01,
            }
            harness.routing_paths.append(routing)

        harness.mark_routed()
        return harness

    def _generate_signal_wires(self, spec_params: dict[str, Any]) -> list[WireSpec]:
        wires = []
        sensor_count = int(spec_params.get("sensor_count", 5))
        for i in range(sensor_count):
            wire = WireSpec(
                wire_id=f"W-SIG-{i + 1:03d}",
                gauge_awg=26,
                conductor_material="copper",
                insulation_type="ptfe",
                length_m=round(0.5 + i * 0.1, 3),
                voltage_rating_v=50.0,
                current_capacity_a=1.0,
                color_code="white",
            )
            wires.append(wire)
        return wires

    def _select_wire_gauge(self, current_a: float) -> int:
        if current_a > 80:
            return 6
        elif current_a > 50:
            return 8
        elif current_a > 30:
            return 10
        elif current_a > 20:
            return 12
        elif current_a > 10:
            return 14
        elif current_a > 5:
            return 16
        elif current_a > 2:
            return 18
        else:
            return 20