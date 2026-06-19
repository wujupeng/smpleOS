from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

_SERVICES_ROOT = Path(__file__).resolve().parents[2] / "services"


def _import_from_service(service_name: str, module_path: str):
    service_dir = str(_SERVICES_ROOT / service_name)
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    if "src" in sys.modules:
        del sys.modules["src"]
        _clear_src_submodules()
    return importlib.import_module(module_path)


def _clear_src_submodules():
    to_remove = [k for k in sys.modules if k.startswith("src.")]
    for k in to_remove:
        del sys.modules[k]


_acd_enums = _import_from_service("aircraft-core-service", "src.domain.enums")
_wfe_enums = _import_from_service("workflow-engine-service", "src.domain.enums")
_ptc_enums = _import_from_service("physics-twin-service", "src.domain.enums")

_acd_aircraft_object = _import_from_service("aircraft-core-service", "src.domain.entities.aircraft_object")
_ptc_physics_model = _import_from_service("physics-twin-service", "src.domain.entities.physics_model")
_ptc_physics_simulation = _import_from_service("physics-twin-service", "src.domain.entities.physics_simulation")
_ptc_digital_twin_runtime = _import_from_service("physics-twin-service", "src.domain.entities.digital_twin_runtime")
_ptc_twin_calibration = _import_from_service("physics-twin-service", "src.domain.entities.twin_calibration")
_wfe_workflow_definition = _import_from_service("workflow-engine-service", "src.domain.entities.workflow_definition")
_wfe_workflow_instance = _import_from_service("workflow-engine-service", "src.domain.entities.workflow_instance")
_ptc_health_assessment = _import_from_service("physics-twin-service", "src.domain.services.health_assessment_service")
_wfe_activity_registry = _import_from_service("workflow-engine-service", "src.infrastructure.handlers.activity_handler_registry")
_wfe_event_mapper = _import_from_service("workflow-engine-service", "src.infrastructure.mappers.event_mapper")


class TestE2EChain1_AircraftObjectLifecycle:

    def test_object_create_version_baseline_impact(self):
        AircraftObject = _acd_aircraft_object.AircraftObject
        ObjectType = _acd_enums.ObjectType
        LifecycleState = _acd_enums.LifecycleState

        obj = AircraftObject(object_type=ObjectType.Component, name="Wing Panel")
        obj.generate_id()
        assert obj.id.startswith("AOBJ-CP-")

        obj.transition_to(LifecycleState.Design, {"requirement_associations": True})
        assert obj.lifecycle_state == LifecycleState.Design

        obj.transition_to(LifecycleState.Manufacturing, {"design_baseline_frozen": True})
        assert obj.lifecycle_state == LifecycleState.Manufacturing


class TestE2EChain2_WorkflowExecution:

    def test_workflow_definition_publish_and_instance(self):
        WorkflowDefinition = _wfe_workflow_definition.WorkflowDefinition
        WorkflowNode = _wfe_workflow_definition.WorkflowNode
        WorkflowEdge = _wfe_workflow_definition.WorkflowEdge
        WorkflowInstance = _wfe_workflow_instance.WorkflowInstance
        NodeExecutionState = _wfe_workflow_instance.NodeExecutionState
        NodeType = _wfe_enums.NodeType
        ConnectionType = _wfe_enums.ConnectionType
        DefinitionStatus = _wfe_enums.DefinitionStatus
        InstanceStatus = _wfe_enums.InstanceStatus

        definition = WorkflowDefinition(
            definition_id="wf-e2e-1",
            name="E2E Test Workflow",
            nodes=[
                WorkflowNode(node_id="n1", type=NodeType.Task, name="Step A", handler="design.rule_check"),
                WorkflowNode(node_id="n2", type=NodeType.Task, name="Step B", handler="verification.cfd_analysis"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_id="n1", target_id="n2"),
            ],
        )
        definition.publish()
        assert definition.status == DefinitionStatus.Published

        instance = WorkflowInstance(
            instance_id="inst-e2e-1",
            definition_id="wf-e2e-1",
            definition_version=1,
            node_states=[
                NodeExecutionState(node_id="n1"),
                NodeExecutionState(node_id="n2"),
            ],
        )
        instance.start()
        assert instance.status == InstanceStatus.Running


class TestE2EChain3_PhysicsTwinLifecycle:

    def test_model_simulation_rom_runtime_calibration(self):
        PhysicsModel = _ptc_physics_model.PhysicsModel
        PhysicsSimulation = _ptc_physics_simulation.PhysicsSimulation
        DigitalTwinRuntime = _ptc_digital_twin_runtime.DigitalTwinRuntime
        TwinCalibration = _ptc_twin_calibration.TwinCalibration
        PhysicsType = _ptc_enums.PhysicsType
        HierarchyLevel = _ptc_enums.HierarchyLevel
        FidelityLevel = _ptc_enums.FidelityLevel
        SolverType = _ptc_enums.SolverType
        SimulationStatus = _ptc_enums.SimulationStatus
        CalibrationStatus = _ptc_enums.CalibrationStatus

        model = PhysicsModel(
            model_id="model-e2e-1",
            name="E2E Wing Model",
            type=PhysicsType.CFD,
            hierarchy_level=HierarchyLevel.Component,
            fidelity_level=FidelityLevel.High,
            aircraft_object_id="AOBJ-CP-E2E",
        )
        validation = model.validate_compatibility()
        assert validation["valid"] is True

        sim = PhysicsSimulation(
            simulation_id="sim-e2e-1",
            model_id="model-e2e-1",
            solver_type=SolverType.OpenFOAM,
        )
        sim.submit()
        assert sim.status == SimulationStatus.Running

        sim.complete()
        assert sim.status == SimulationStatus.Completed

        runtime = DigitalTwinRuntime(
            runtime_id="rt-e2e-1",
            aircraft_object_id="AOBJ-CP-E2E",
        )
        result = runtime.update_with_sensor_data({"temperature": 85.0, "pressure": 101325.0})
        assert "prediction_output" in result

        indicator = runtime.compute_health_indicator("wing-001", predicted=85.0, measured=84.5)
        assert indicator.score > 0

        cal = TwinCalibration(
            calibration_id="cal-e2e-1",
            runtime_id="rt-e2e-1",
            model_id="model-e2e-1",
        )
        cal.execute()
        assert cal.status == CalibrationStatus.InProgress

        passed = cal.validate_calibration(holdout_error=0.03)
        assert passed is True


class TestE2EChain4_CrossPillarIntegration:

    def test_object_change_triggers_workflow(self):
        AircraftObject = _acd_aircraft_object.AircraftObject
        ObjectType = _acd_enums.ObjectType
        ActivityHandlerRegistry = _wfe_activity_registry.ActivityHandlerRegistry

        obj = AircraftObject(object_type=ObjectType.Component, name="Changed Part")
        obj.generate_id()

        handler = ActivityHandlerRegistry.get_handler("design.rule_check")
        assert handler is not None

        result = handler.execute({"model_id": obj.id, "rule_set_id": "rs-1"})
        assert "violations" in result


class TestE2EChain5_EventTriggerIntegration:

    def test_event_mapping(self):
        get_event_mapping = _wfe_event_mapper.get_event_mapping
        mapping = get_event_mapping("design.baseline.frozen")
        assert mapping is not None
        assert mapping["trigger_name"] == "DesignVerificationTrigger"
        assert mapping["workflow_template"] == "DesignVerificationWorkflow"

    def test_event_mapping_not_found(self):
        get_event_mapping = _wfe_event_mapper.get_event_mapping
        mapping = get_event_mapping("nonexistent.event")
        assert mapping is None


class TestE2EChain6_HealthAlertToMaintenanceWorkflow:

    def test_health_alert_triggers_workflow(self):
        DigitalTwinRuntime = _ptc_digital_twin_runtime.DigitalTwinRuntime
        get_event_mapping = _wfe_event_mapper.get_event_mapping

        runtime = DigitalTwinRuntime(aircraft_object_id="AOBJ-AC-001")

        indicator = runtime.compute_health_indicator("engine-001", predicted=100.0, measured=50.0)
        assert indicator.score < 60

        mapping = get_event_mapping("fleet.twin.anomaly.detected")
        assert mapping is not None
        assert mapping["workflow_template"] == "FRACASWorkflow"
