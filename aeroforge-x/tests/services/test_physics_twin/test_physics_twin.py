import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'physics-twin-service'))

from src.domain.enums import (
    CalibrationStatus, FidelityLevel, HealthStatus, HierarchyLevel,
    ModelStatus, PhysicsType, ReductionMethod, SimulationStatus, SolverType, ValidationStatus,
)
from src.domain.entities.physics_model import PhysicsModel
from src.domain.entities.physics_simulation import PhysicsSimulation
from src.domain.entities.reduced_order_model import ReducedOrderModel
from src.domain.entities.digital_twin_runtime import DigitalTwinRuntime, HealthIndicator, RULPrediction
from src.domain.entities.twin_calibration import TwinCalibration
from src.domain.services.health_assessment_service import HealthAssessmentService


class TestPhysicsModel:

    def test_create_model(self):
        model = PhysicsModel(
            name="Wing CFD Model",
            type=PhysicsType.CFD,
            hierarchy_level=HierarchyLevel.Component,
            fidelity_level=FidelityLevel.Mid,
            aircraft_object_id="AOBJ-CP-001",
        )
        assert model.name == "Wing CFD Model"
        assert model.status == ModelStatus.Draft

    def test_compatibility_check_valid(self):
        model = PhysicsModel(
            name="Valid Model",
            type=PhysicsType.CFD,
            hierarchy_level=HierarchyLevel.Component,
            fidelity_level=FidelityLevel.Mid,
            aircraft_object_id="AOBJ-CP-001",
        )
        result = model.validate_compatibility()
        assert result["valid"] is True

    def test_compatibility_check_invalid(self):
        model = PhysicsModel(
            name="Invalid Model",
            type=PhysicsType.CFD,
            hierarchy_level=HierarchyLevel.Detail,
            fidelity_level=FidelityLevel.Low,
            aircraft_object_id="AOBJ-CP-001",
        )
        result = model.validate_compatibility()
        assert result["valid"] is False

    def test_switch_fidelity(self):
        model = PhysicsModel(
            name="Test",
            type=PhysicsType.FEA,
            hierarchy_level=HierarchyLevel.Component,
            fidelity_level=FidelityLevel.Low,
            aircraft_object_id="AOBJ-CP-001",
        )
        model.switch_fidelity(FidelityLevel.High)
        assert model.fidelity_level == FidelityLevel.High


class TestPhysicsSimulation:

    def test_simulation_lifecycle(self):
        sim = PhysicsSimulation(
            model_id="model-1",
            solver_type=SolverType.OpenFOAM,
        )
        assert sim.status == SimulationStatus.Queued

        sim.submit()
        assert sim.status == SimulationStatus.Running

        sim.complete()
        assert sim.status == SimulationStatus.Completed

    def test_simulation_cancel(self):
        sim = PhysicsSimulation(model_id="model-1", solver_type=SolverType.OpenFOAM)
        sim.submit()
        sim.cancel()
        assert sim.status == SimulationStatus.Failed


class TestReducedOrderModel:

    def test_rom_validation_passed(self):
        rom = ReducedOrderModel(
            source_model_id="model-1",
            method=ReductionMethod.POD,
            validation_error=0.03,
        )
        rom.validate_rom(error_threshold=0.05)
        assert rom.validation_status == ValidationStatus.Passed

    def test_rom_validation_failed(self):
        rom = ReducedOrderModel(
            source_model_id="model-1",
            method=ReductionMethod.POD,
            validation_error=0.10,
        )
        rom.validate_rom(error_threshold=0.05)
        assert rom.validation_status == ValidationStatus.Failed

    def test_rom_deploy_unvalidated(self):
        rom = ReducedOrderModel(
            source_model_id="model-1",
            method=ReductionMethod.POD,
            validation_error=0.10,
        )
        with pytest.raises(ValueError):
            rom.deploy("runtime-1")


class TestDigitalTwinRuntime:

    def test_runtime_creation(self):
        runtime = DigitalTwinRuntime(aircraft_object_id="AOBJ-AC-001")
        assert runtime.active_fidelity == FidelityLevel.Low
        assert runtime.data_lagged is False

    def test_sensor_data_update(self):
        runtime = DigitalTwinRuntime(aircraft_object_id="AOBJ-AC-001")
        result = runtime.update_with_sensor_data({"temperature": 85.5})
        assert "prediction_output" in result
        assert runtime.data_lagged is False

    def test_health_indicator(self):
        runtime = DigitalTwinRuntime(aircraft_object_id="AOBJ-AC-001")
        indicator = runtime.compute_health_indicator("wing-001", predicted=100.0, measured=95.0)
        assert indicator.score > 0
        assert indicator.status in (HealthStatus.Healthy, HealthStatus.Warning, HealthStatus.Critical)

    def test_data_lagged(self):
        runtime = DigitalTwinRuntime(aircraft_object_id="AOBJ-AC-001")
        runtime.mark_data_lagged()
        assert runtime.data_lagged is True


class TestTwinCalibration:

    def test_calibration_lifecycle(self):
        cal = TwinCalibration(runtime_id="rt-1", model_id="model-1")
        assert cal.status == CalibrationStatus.Pending

        cal.execute()
        assert cal.status == CalibrationStatus.InProgress

        cal.complete()
        assert cal.status == CalibrationStatus.Completed

    def test_calibration_validation_passed(self):
        cal = TwinCalibration(runtime_id="rt-1", model_id="model-1")
        result = cal.validate_calibration(holdout_error=0.03, threshold=0.05)
        assert result is True

    def test_calibration_validation_failed(self):
        cal = TwinCalibration(runtime_id="rt-1", model_id="model-1")
        result = cal.validate_calibration(holdout_error=0.10, threshold=0.05)
        assert result is False


class TestHealthAssessmentService:

    def test_compute_health_healthy(self):
        indicator = HealthAssessmentService.compute_health(100.0, 98.0, "wing-001")
        assert indicator.score >= 80
        assert indicator.status == HealthStatus.Healthy

    def test_compute_health_warning(self):
        indicator = HealthAssessmentService.compute_health(100.0, 85.0, "wing-001")
        assert indicator.status in (HealthStatus.Warning, HealthStatus.Critical)

    def test_predict_rul(self):
        prediction = HealthAssessmentService.predict_rul("wing-001", 0.01, 80.0, threshold=0.0)
        assert prediction.rul_value > 0
        assert prediction.confidence == 0.9

    def test_diagnose_anomaly(self):
        result = HealthAssessmentService.diagnose_anomaly(100.0, 95.0, "wing-001", threshold=0.1)
        assert "is_anomaly" in result
        assert "deviation" in result