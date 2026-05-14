import asyncio
import json
import logging
from typing import Callable, TypeVar
from pydantic import BaseModel, ValidationError
import google.generativeai as genai
from app.config import settings
from app.core import WorkflowError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
_MAX_RETRIES = 2

class GeminiCorrectionLoop:
    def __init__(self, model_name: str = settings.gemini_model) -> None:
        self._model = genai.GenerativeModel(model_name)

    async def generate_and_validate(
        self,
        prompt: str,
        output_model: type[T],
        task_id: str = "",
        response_parser: Callable[[str], dict] | None = None,
    ) -> T:
        parser = response_parser or self._strip_and_parse_json
        loop = asyncio.get_running_loop()
        last_error = ""
        for attempt in range(_MAX_RETRIES + 1):
            current_prompt = self._build_retry_prompt(prompt, last_error, attempt)
            response = await loop.run_in_executor(
                None,
                lambda p=current_prompt: self._model.generate_content(p),
            )
            try:
                data = parser(response.text)
                result = output_model(**data)
                logger.info("Gemini generation succeeded on attempt %d", attempt + 1)
                return result
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)
                logger.warning("Gemini attempt %d/%d failed: %s", attempt + 1, _MAX_RETRIES + 1, last_error)
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
