import logging
from app.errors import WorkflowError
from app.progress import report_progress
from app.task_client import TaskServiceClient

logger = logging.getLogger(__name__)

class WorkflowErrorHandler:
    def __init__(self, compiled_graph, task_client: TaskServiceClient) -> None:
        self._graph = compiled_graph
        self._task_client = task_client

    async def run(self, state: dict) -> None:
        task_id = state["task_id"]
        try:
            final_state = await self._graph.ainvoke(state)
            final_status = final_state.get("status", "completed")
            error_message = final_state.get("error") or None
            await self._task_client.update_status(task_id, final_status, error_message=error_message)
            if final_status in ("failed", "cancelled"):
                await report_progress(task_id, "workflow", final_status, 0)
            logger.info("Workflow finished: task_id=%s status=%s", task_id, final_status)
        except WorkflowError as exc:
            logger.error("WorkflowError: task_id=%s error=%s", task_id, exc)
            await self._task_client.update_status(task_id, "failed", error_message=str(exc))
            await report_progress(task_id, "workflow", "failed", 0)
        except Exception as exc:
            logger.error("Unexpected workflow failure: task_id=%s error=%s", task_id, exc)
            await self._task_client.update_status(task_id, "failed", error_message=str(exc))
            await report_progress(task_id, "workflow", "failed", 0)
