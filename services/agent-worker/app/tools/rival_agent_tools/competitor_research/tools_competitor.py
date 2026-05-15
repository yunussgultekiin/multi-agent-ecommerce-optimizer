import asyncio
import logging
from google.genai import types
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from app.gemini_client import call_gemini
from .models_competitor import CompetitorResult, MIN_VALID_COMPETITORS, MAX_VALID_COMPETITORS
from .prompts_competitor import build_competitor_prompt
from .utils_competitor import log_research_summary, log_tool_call, parse_json_response

logger = logging.getLogger(__name__)

_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


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
            response_text, grounding_hit = await call_gemini(
                model=settings.gemini_flash_model,
                prompt=prompt,
                config=types.GenerateContentConfig(
                    tools=[_SEARCH_TOOL],
                    temperature=0.2,
                    max_output_tokens=800 if attempt > 0 else 1200,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
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
        settings.gemini_flash_model,
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
