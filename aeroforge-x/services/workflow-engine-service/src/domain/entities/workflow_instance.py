from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import InstanceStatus, NodeStatus


class NodeExecutionState(BaseModel):
    node_id: str
    status: NodeStatus = NodeStatus.Pending
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class HumanTask(BaseModel):
    task_id: str = ""
    instance_id: str
    node_id: str
    type: str
    assignee: str
    status: str = "Pending"
    deadline: datetime | None = None
    escalated_to: str = ""
    decision: str = ""
    comments: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class EventTrigger(BaseModel):
    trigger_id: str = ""
    definition_id: str
    trigger_type: str
    event_pattern: str = ""
    cron_expression: str = ""
    condition: str = ""
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowInstance(BaseModel):
    instance_id: str = ""
    definition_id: str
    definition_version: int = 1
    status: InstanceStatus = InstanceStatus.Created
    input_parameters: dict[str, Any] = Field(default_factory=dict)
    output_parameters: dict[str, Any] = Field(default_factory=dict)
    node_states: list[NodeExecutionState] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    human_tasks: list[HumanTask] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def start(self) -> None:
        if self.status != InstanceStatus.Created:
            raise ValueError(f"Cannot start instance in {self.status.value} state")
        self.status = InstanceStatus.Running
        self.started_at = datetime.utcnow()

    def suspend(self) -> None:
        if self.status != InstanceStatus.Running:
            raise ValueError(f"Cannot suspend instance in {self.status.value} state")
        self.status = InstanceStatus.Suspended

    def resume(self) -> None:
        if self.status != InstanceStatus.Suspended:
            raise ValueError(f"Cannot resume instance in {self.status.value} state")
        self.status = InstanceStatus.Running

    def cancel(self) -> None:
        if self.status not in (InstanceStatus.Running, InstanceStatus.Suspended):
            raise ValueError(f"Cannot cancel instance in {self.status.value} state")
        self.status = InstanceStatus.Failed
        self.completed_at = datetime.utcnow()

    def complete(self) -> None:
        self.status = InstanceStatus.Completed
        self.completed_at = datetime.utcnow()

    def fail(self, error_message: str = "") -> None:
        self.status = InstanceStatus.Failed
        self.completed_at = datetime.utcnow()

    def retry_node(self, node_id: str) -> None:
        for ns in self.node_states:
            if ns.node_id == node_id and ns.status == NodeStatus.Failed:
                ns.status = NodeStatus.Pending
                ns.retry_count += 1
                ns.error_message = ""
                break
        if self.status == InstanceStatus.Failed:
            self.status = InstanceStatus.Running