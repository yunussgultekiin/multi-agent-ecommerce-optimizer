from app.core import WorkflowError
from app.redis import report_progress
from app.task_client import TaskServiceClient
import logging

logger = logging.getLogger(__name__)

class WorkflowErrorHandler:
    def __init__(self, compiled_graph, task_client: TaskServiceClient) -> None:
        self._graph = compiled_graph
        self._task_client = task_client

    async def run(self, state: dict) -> dict:
        task_id = state["task_id"]
        try:
            final_state = await self._graph.ainvoke(state)
            final_status = final_state.get("status", "completed")
            error_message = final_state.get("error") or None

            await self._task_client.update_status(
                task_id,
                final_status,
                error_message=error_message,
            )

            if final_status in ("failed", "cancelled"):
                await report_progress(task_id, "workflow", final_status, 0)

            logger.info(
                "Workflow finished: task_id=%s status=%s", task_id, final_status
            )
            return final_state

        except WorkflowError as exc:
            logger.error("WorkflowError: task_id=%s error=%s", task_id, exc)
            await self._task_client.update_status(
                task_id,
                "failed",
                error_message=str(exc),
            )
            await report_progress(task_id, "workflow", "failed", 0)
            return {
                **state,
                "status": "failed",
                "error": str(exc),
            }

        except Exception as exc:
            logger.error(
                "Unexpected workflow failure: task_id=%s error=%s", task_id, exc
            )
            await self._task_client.update_status(
                task_id,
                "failed",
                error_message=str(exc),
            )
            await report_progress(task_id, "workflow", "failed", 0)
            return {
                **state,
                "status": "failed",
                "error": str(exc),
            }
