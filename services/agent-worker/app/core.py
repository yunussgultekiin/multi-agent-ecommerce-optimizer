from dataclasses import dataclass, field

class WorkflowError(Exception):
    def __init__(self, message: str, task_id: str = "") -> None:
        super().__init__(message)
        self.task_id = task_id

@dataclass
class ToolResult:
    success: bool
    data: dict = field(default_factory=dict)
    fallback_used: bool = False
