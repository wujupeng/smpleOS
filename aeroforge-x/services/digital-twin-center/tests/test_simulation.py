import pytest

from services.digital_twin_center.src.domain.entities.simulation_models import (
    SimulationModel, SimulationStatus, FlightState,
)
from services.digital_twin_center.src.domain.services.realtime_simulation_service import RealtimeSimulationService


class TestFlightState:
    def test_to_dict(self) -> None:
        state = FlightState(altitude_m=1000, airspeed_ms=50.0, heading_deg=90.0)
        d = state.to_dict()
        assert d["altitude_m"] == 1000.0
        assert d["airspeed_ms"] == 50.0


class TestRealtimeSimulationService:
    def test_setup_simulation_model(self) -> None:
        service = RealtimeSimulationService()
        model = service.setup_simulation_model("AC-001")
        assert model.aircraft_sn == "AC-001"
        assert "lift" in model.rom_coefficients
        assert "drag" in model.rom_coefficients

    def test_setup_with_custom_params(self) -> None:
        service = RealtimeSimulationService()
        model = service.setup_simulation_model(
            "AC-001",
            structural_params={"wing_span": 20.0, "wing_area": 40.0, "mass_kg": 2000.0, "moment_of_inertia": 80000.0},
            aero_params={"cl_alpha": 6.0, "cd0": 0.03, "cl_max": 1.8, "oswald_efficiency": 0.9},
        )
        assert model.structural_params["wing_span"] == 20.0

    def test_start_stop_simulation(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        assert service.start_simulation("AC-001") is True
        status = service.get_simulation_status("AC-001")
        assert status["status"] == "running"
        assert service.stop_simulation("AC-001") is True

    def test_start_nonexistent(self) -> None:
        service = RealtimeSimulationService()
        assert service.start_simulation("AC-999") is False

    def test_run_realtime_simulation(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        service.start_simulation("AC-001")

        initial_state = FlightState(
            altitude_m=1000.0,
            airspeed_ms=50.0,
            heading_deg=90.0,
            pitch_deg=2.0,
            engine_rpm=3000.0,
            fuel_kg=100.0,
        )

        result = service.run_realtime_simulation("AC-001", initial_state, dt_seconds=0.1)
        assert result is not None
        assert result.predicted_state.altitude_m >= 0
        assert result.step_number == 1

    def test_simulation_not_running(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        result = service.run_realtime_simulation("AC-001")
        assert result is None

    def test_multiple_steps(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        service.start_simulation("AC-001")

        state = FlightState(altitude_m=1000, airspeed_ms=50, pitch_deg=2, engine_rpm=3000, fuel_kg=100)
        for _ in range(5):
            service.run_realtime_simulation("AC-001", state)

        results = service.get_results("AC-001")
        assert len(results) == 5

    def test_compare_actual_vs_predicted(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        service.start_simulation("AC-001")

        state = FlightState(altitude_m=1000, airspeed_ms=50, pitch_deg=2, engine_rpm=3000, fuel_kg=100)
        service.run_realtime_simulation("AC-001", state)

        actual = FlightState(altitude_m=1010, airspeed_ms=51, pitch_deg=2.1, engine_rpm=3000, fuel_kg=99.9)
        comparison = service.compare_actual_vs_predicted("AC-001", actual)
        assert comparison is not None
        assert "deviation" in comparison

    def test_calibrate_model(self) -> None:
        service = RealtimeSimulationService()
        model = service.setup_simulation_model("AC-001")
        model.deviation_accumulated = 0.5

        result = service.calibrate_model("AC-001")
        assert result is not None
        assert result.improvement_pct > 0
        assert model.calibration_count == 1

    def test_get_simulation_status(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        service.start_simulation("AC-001")

        status = service.get_simulation_status("AC-001")
        assert status is not None
        assert status["status"] == "running"

    def test_get_status_nonexistent(self) -> None:
        service = RealtimeSimulationService()
        assert service.get_simulation_status("AC-999") is None

    def test_pause_simulation(self) -> None:
        service = RealtimeSimulationService()
        service.setup_simulation_model("AC-001")
        service.start_simulation("AC-001")
        assert service.pause_simulation("AC-001") is True
        status = service.get_simulation_status("AC-001")
        assert status["status"] == "paused"