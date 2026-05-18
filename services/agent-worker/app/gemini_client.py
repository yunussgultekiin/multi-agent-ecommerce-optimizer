from app.config import settings
from google import genai
import google.api_core.exceptions
import google.auth.exceptions
from google.genai import errors as genai_errors
from google.genai import types
from google.genai.types import HttpOptions
import logging

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            http_options=HttpOptions(api_version="v1"),
        )
    return _client


def _reset_client() -> genai.Client:
    global _client
    _client = genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        http_options=HttpOptions(api_version="v1"),
    )
    return _client


async def call_gemini(
    model: str,
    prompt: str,
    config: types.GenerateContentConfig,
) -> tuple[str, bool]:
    logger.debug(
        "call_gemini | model=%s project=%s location=%s",
        model,
        settings.google_cloud_project,
        settings.google_cloud_location,
    )
    client = _get_client()
    config.automatic_function_calling = types.AutomaticFunctionCallingConfig(
        disable=True
    )
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
    except RuntimeError as exc:
        if "closed" in str(exc).lower():
            logger.warning("Gemini client was closed, resetting | model=%s", model)
            client = _reset_client()
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
        else:
            raise
    except google.auth.exceptions.DefaultCredentialsError as exc:
        raise RuntimeError(
            "Google Cloud credentials not configured. "
            "Run: gcloud auth application-default login"
        ) from exc
    except google.api_core.exceptions.NotFound as exc:
        raise RuntimeError(
            f"Model '{model}' not found | project='{settings.google_cloud_project}' "
            f"location='{settings.google_cloud_location}' | {exc}"
        ) from exc
    except google.api_core.exceptions.PermissionDenied as exc:
        raise RuntimeError(
            f"Permission denied | project='{settings.google_cloud_project}' | {exc}"
        ) from exc
    except genai_errors.ClientError as exc:
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc)
        raise RuntimeError(
            f"Gemini client error [{code}] | model='{model}' | {message}"
        ) from exc
    except genai_errors.ServerError as exc:
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc)
        raise RuntimeError(
            f"Gemini server error [{code}] | model='{model}' | {message}"
        ) from exc

    grounding_hit = bool(
        getattr(
            getattr(
                (getattr(response, "candidates", None) or [{}])[0],
                "grounding_metadata",
                None,
            ),
            "grounding_chunks",
            None,
        )
    )

    try:
        text = response.text or ""
    except Exception:
        text = ""

    if not text.strip():
        finish_reason = None
        try:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                finish_reason = getattr(candidates[0], "finish_reason", None)
        except Exception:
            pass
        logger.warning(
            "call_gemini returned empty text | model=%s finish_reason=%s grounding=%s",
            model,
            finish_reason,
            grounding_hit,
        )

    return text, grounding_hit
