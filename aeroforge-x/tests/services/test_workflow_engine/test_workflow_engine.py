import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'services', 'workflow-engine-service'))

from src.domain.enums import ConnectionType, DefinitionStatus, InstanceStatus, NodeType, TriggerType
from src.domain.entities.workflow_definition import WorkflowDefinition, WorkflowNode, WorkflowEdge
from src.domain.entities.workflow_instance import WorkflowInstance, NodeExecutionState, HumanTask, EventTrigger


class TestWorkflowDefinition:

    def test_create_definition(self):
        definition = WorkflowDefinition(
            definition_id="wf-1",
            name="Test Workflow",
            nodes=[
                WorkflowNode(node_id="n1", type=NodeType.Task, name="Step 1", handler="test.handler"),
                WorkflowNode(node_id="n2", type=NodeType.Task, name="Step 2", handler="test.handler2"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_id="n1", target_id="n2", connection_type=ConnectionType.Sequence),
            ],
        )
        assert definition.name == "Test Workflow"
        assert definition.status == DefinitionStatus.Draft
        assert len(definition.nodes) == 2

    def test_validate_dag_valid(self):
        definition = WorkflowDefinition(
            name="Valid DAG",
            nodes=[
                WorkflowNode(node_id="n1", type=NodeType.Task, name="A", handler="h1"),
                WorkflowNode(node_id="n2", type=NodeType.Task, name="B", handler="h2"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_id="n1", target_id="n2"),
            ],
        )
        result = definition.validate_dag()
        assert result["valid"] is True

    def test_validate_dag_circular(self):
        definition = WorkflowDefinition(
            name="Circular DAG",
            nodes=[
                WorkflowNode(node_id="n1", type=NodeType.Task, name="A", handler="h1"),
                WorkflowNode(node_id="n2", type=NodeType.Task, name="B", handler="h2"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_id="n1", target_id="n2"),
                WorkflowEdge(edge_id="e2", source_id="n2", target_id="n1"),
            ],
        )
        result = definition.validate_dag()
        assert result["valid"] is False

    def test_publish_definition(self):
        definition = WorkflowDefinition(
            name="Publishable",
            nodes=[WorkflowNode(node_id="n1", type=NodeType.Task, name="A", handler="h1")],
            edges=[],
        )
        definition.publish()
        assert definition.status == DefinitionStatus.Published

    def test_publish_invalid_definition(self):
        definition = WorkflowDefinition(
            name="Invalid",
            nodes=[],
            edges=[],
        )
        with pytest.raises(ValueError):
            definition.publish()


class TestWorkflowInstance:

    def test_instance_lifecycle(self):
        instance = WorkflowInstance(
            instance_id="inst-1",
            definition_id="wf-1",
            definition_version=1,
        )
        assert instance.status == InstanceStatus.Created

        instance.start()
        assert instance.status == InstanceStatus.Running

        instance.suspend()
        assert instance.status == InstanceStatus.Suspended

        instance.resume()
        assert instance.status == InstanceStatus.Running

    def test_instance_cancel(self):
        instance = WorkflowInstance(definition_id="wf-1")
        instance.start()
        instance.cancel()
        assert instance.status == InstanceStatus.Failed

    def test_retry_node(self):
        instance = WorkflowInstance(
            definition_id="wf-1",
            node_states=[
                NodeExecutionState(node_id="n1", status="Failed"),
            ],
        )
        instance.status = InstanceStatus.Failed
        instance.retry_node("n1")
        assert instance.node_states[0].retry_count == 1

    def test_human_task(self):
        task = HumanTask(
            instance_id="inst-1",
            node_id="n1",
            type="Approval",
            assignee="user1",
        )
        assert task.status == "Pending"
        assert task.type == "Approval"


class TestEventTrigger:

    def test_trigger_creation(self):
        trigger = EventTrigger(
            definition_id="wf-1",
            trigger_type=TriggerType.EventDriven.value,
            event_pattern="design.baseline.frozen",
        )
        assert trigger.trigger_type == "EventDriven"
        assert trigger.enabled is True