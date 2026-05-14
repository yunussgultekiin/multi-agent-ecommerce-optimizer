import asyncio
import logging
import google.auth.exceptions
import google.api_core.exceptions
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from .models_competitor import CompetitorResult, MIN_VALID_COMPETITORS, MAX_VALID_COMPETITORS
from .prompts_competitor import build_competitor_prompt
from .utils_competitor import log_research_summary, log_tool_call, parse_json_response

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)

_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


async def _call_gemini(prompt: str, max_output_tokens: int = 1200) -> tuple[str, bool]:
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=settings.gemini_research_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[_SEARCH_TOOL],
                    temperature=0.2,
                    max_output_tokens=max_output_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            ),
        )
    except google.auth.exceptions.DefaultCredentialsError as exc:
        raise RuntimeError(
            "Google Cloud credentials not configured. "
            "Run: gcloud auth application-default login"
        ) from exc
    except google.api_core.exceptions.NotFound as exc:
        raise RuntimeError(
            f"Model '{settings.gemini_research_model}' not found in "
            f"region '{settings.google_cloud_location}'."
        ) from exc
    except google.api_core.exceptions.PermissionDenied as exc:
        raise RuntimeError(
            f"Permission denied for project '{settings.google_cloud_project}'."
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
    return response.text or "", grounding_hit


async def _research_one(
    competitor_name: str,
    category: str,
    platform: str,
    max_retries: int = 1,
) -> ToolResult:
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        correction_context = (
            f"Validation or JSON parsing failed:\n{last_error}\n\n"
            "Return ONLY valid JSON matching the schema. "
            "Use null for unavailable numeric fields. Use [] for list fields."
            if attempt > 0
            else None
        )

        try:
            prompt = build_competitor_prompt(
                competitor_name=competitor_name,
                category=category,
                platform=platform,
                correction_context=correction_context,
            )
            response_text, grounding_hit = await _call_gemini(
                prompt,
                max_output_tokens=800 if attempt > 0 else 1200,
            )
            data = parse_json_response(response_text)
            data["platform"] = platform
            if not data.get("competitor_name"):
                data["competitor_name"] = competitor_name

            result = CompetitorResult(**data)
            fallback_used = attempt > 0

            log_tool_call(
                competitor_name=competitor_name,
                platform=platform,
                estimated_price=result.estimated_price,
                feature_count=len(result.features),
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
            )

            return ToolResult(
                success=True,
                data=result.model_dump(),
                fallback_used=fallback_used,
            )

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "CompetitorResearchTool validation failed | attempt=%d competitor=%s error=%s",
                attempt + 1,
                competitor_name,
                last_error,
            )
            if attempt == max_retries:
                break

        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "CompetitorResearchTool error | competitor=%s error=%s",
                competitor_name,
                last_error,
            )
            break

    log_tool_call(
        competitor_name=competitor_name,
        platform=platform,
        estimated_price=None,
        feature_count=0,
        grounding_hit=False,
        fallback_used=True,
    )
    return ToolResult(
        success=False,
        fallback_used=True,
        data={"error": f"Research failed: {last_error or 'unknown error'}"},
    )


async def run_competitor_research_tool(
    competitors: list[dict],
    category: str,
) -> list[ToolResult]:
    if not isinstance(competitors, list):
        raise ValueError("competitors must be a list")

    category = category.strip() if isinstance(category, str) and category.strip() else "general"
    competitors = competitors[:MAX_VALID_COMPETITORS]
    input_count = len(competitors)

    logger.info(
        "Researching %d competitors | category=%s | model=%s",
        input_count,
        category,
        settings.gemini_research_model,
    )

    raw_results = await asyncio.gather(
        *[
            _research_one(
                competitor_name=c.get("competitor_name", ""),
                category=category,
                platform=c.get("platform", ""),
            )
            for c in competitors
            if c.get("competitor_name")
        ],
        return_exceptions=True,
    )

    tool_results: list[ToolResult] = []
    for competitor, result in zip(competitors, raw_results):
        if isinstance(result, Exception):
            logger.exception(
                "Unexpected research error | competitor=%s",
                competitor.get("competitor_name", "unknown"),
            )
            tool_results.append(
                ToolResult(success=False, fallback_used=True, data={"error": str(result)})
            )
        else:
            tool_results.append(result)

    successful_count = sum(1 for r in tool_results if r.success)
    fallback_used = successful_count < input_count

    log_research_summary(
        input_count=input_count,
        processed_count=len(tool_results),
        successful_count=successful_count,
        fallback_used=fallback_used,
    )

    return tool_results
