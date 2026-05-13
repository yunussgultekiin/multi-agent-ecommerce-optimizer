class WorkflowError(Exception):
    def __init__(self, message: str, task_id: str = "") -> None:
        super().__init__(message)
        self.task_id = task_id
