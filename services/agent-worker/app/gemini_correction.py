from app.config import settings
from app.core import WorkflowError
import asyncio
from google import genai
import google.api_core.exceptions
import google.auth.exceptions
from google.genai import types
from google.genai.types import HttpOptions
import json
import logging
from pydantic import BaseModel, ValidationError
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
_MAX_RETRIES = 2
_CALL_TIMEOUT_SECONDS = 30

class GeminiCorrectionLoop:
    def __init__(self, model_name: str = "gemini-2.5-flash-lite") -> None:
        self._model_name = model_name

    async def generate_and_validate(
        self,
        prompt: str,
        output_model: type[T],
        task_id: str = "",
        response_parser: Callable[[str], dict] | None = None,
    ) -> T:

        parser = response_parser or self._strip_and_parse_json
        last_error = ""
        for attempt in range(_MAX_RETRIES + 1):
            current_prompt = self._build_retry_prompt(prompt, last_error, attempt)
            client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
                http_options=HttpOptions(api_version="v1"),
            )
            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self._model_name,
                        contents=current_prompt,
                        config=types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=0),
                        ),
                    ),
                    timeout=_CALL_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                last_error = f"timed out after {_CALL_TIMEOUT_SECONDS}s"
                logger.warning(
                    "Gemini call timed out | attempt=%d/%d model=%s",
                    attempt + 1, _MAX_RETRIES + 1, self._model_name,
                )
                continue
            except google.auth.exceptions.DefaultCredentialsError as exc:
                raise WorkflowError(
                    "Google Cloud credentials not configured. "
                    "Run: gcloud auth application-default login",
                    task_id=task_id,
                ) from exc
            except google.api_core.exceptions.NotFound as exc:
                raise WorkflowError(
                    f"Model '{self._model_name}' not found in region '{settings.google_cloud_location}'. "
                    "Check the model name and location.",
                    task_id=task_id,
                ) from exc
            except google.api_core.exceptions.PermissionDenied as exc:
                raise WorkflowError(
                    f"Permission denied. Ensure the account has the 'Vertex AI User' role "
                    f"in project '{settings.google_cloud_project}'.",
                    task_id=task_id,
                ) from exc

            try:
                raw_text = response.text or ""
            except Exception:
                raw_text = ""

            if not raw_text.strip():
                last_error = "Gemini returned empty response"
                logger.warning(
                    "Gemini empty response | attempt=%d/%d model=%s",
                    attempt + 1, _MAX_RETRIES + 1, self._model_name,
                )
                continue

            try:
                data = parser(raw_text)
                result = output_model(**data)
                logger.info("Gemini generation succeeded on attempt %d", attempt + 1)
                return result
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)
                logger.warning(
                    "Gemini attempt %d/%d failed: %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    last_error,
                )

        raise WorkflowError(
            f"Gemini self-correction exhausted after {_MAX_RETRIES + 1} attempts. Last error: {last_error}",
            task_id=task_id,
        )

    @staticmethod
    def _build_retry_prompt(original_prompt: str, last_error: str, attempt: int) -> str:
        if attempt == 0 or not last_error:
            return original_prompt
        return (
            f"PREVIOUS ATTEMPT FAILED.\nValidation error:\n{last_error}\n\n"
            f"Fix these errors and return ONLY valid JSON.\n\nOriginal task:\n{original_prompt}"
        )

    @staticmethod
    def _strip_and_parse_json(raw_text: str) -> dict:
        text = raw_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
