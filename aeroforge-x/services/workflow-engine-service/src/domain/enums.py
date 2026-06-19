from enum import Enum


class NodeType(str, Enum):
    Task = "Task"
    Gateway = "Gateway"
    Event = "Event"
    SubWorkflow = "SubWorkflow"


class ConnectionType(str, Enum):
    Sequence = "Sequence"
    Parallel = "Parallel"
    Conditional = "Conditional"


class DefinitionStatus(str, Enum):
    Draft = "Draft"
    Published = "Published"
    Deprecated = "Deprecated"


class InstanceStatus(str, Enum):
    Created = "Created"
    Running = "Running"
    Suspended = "Suspended"
    Completed = "Completed"
    Failed = "Failed"


class NodeStatus(str, Enum):
    Pending = "Pending"
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"
    Skipped = "Skipped"


class FailureStrategy(str, Enum):
    Retry = "Retry"
    Skip = "Skip"
    Rollback = "Rollback"
    ManualIntervention = "ManualIntervention"


class TriggerType(str, Enum):
    EventDriven = "EventDriven"
    Scheduled = "Scheduled"
    Conditional = "Conditional"


class HumanTaskType(str, Enum):
    Approval = "Approval"
    Review = "Review"
    Decision = "Decision"


class HumanTaskStatus(str, Enum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"
    Escalated = "Escalated"
    Completed = "Completed"