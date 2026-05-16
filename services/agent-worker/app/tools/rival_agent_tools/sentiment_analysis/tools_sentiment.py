from .models_sentiment import SentimentResult
from .prompts_sentiment import (
    build_fallback_sentiment_prompt,
    build_self_correction_prompt,
    build_sentiment_prompt,
)
from .utils_sentiment import (
    extract_competitor_names,
    extract_research_context,
    log_tool_call,
    parse_json_response,
)
from app.config import settings
from app.core import ToolResult
from app.gemini_client import call_gemini
from google.genai import types
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)
_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())

async def run_sentiment_analyzer(
    competitor_names: list[dict],
    competitor_research_results: list[dict],
    category: str,
    target_platform: str,
    user_product: dict,
    max_retries: int = 2,
) -> ToolResult:
    category = (
        category.strip()
        if isinstance(category, str) and category.strip()
        else "general"
    )
    product_title = user_product.get("title", "").strip()
    brand = user_product.get("brand", "").strip()

    names = extract_competitor_names(competitor_names)
    research_context = extract_research_context(competitor_research_results)
    fallback_used = len(names) == 0

    if fallback_used:
        base_prompt = build_fallback_sentiment_prompt(
            category=category,
            target_platform=target_platform,
            product_title=product_title,
            brand=brand,
        )
    else:
        base_prompt = build_sentiment_prompt(
            competitor_names=names,
            category=category,
            target_platform=target_platform,
            product_title=product_title,
            brand=brand,
            research_context=research_context,
        )

    last_error: str | None = None
    grounding_hit = False

    for attempt in range(max_retries + 1):
        if attempt > 0:
            fallback_used = True

        current_prompt = (
            build_self_correction_prompt(base_prompt, last_error)
            if attempt > 0
            else base_prompt
        )

        try:
            response_text, grounding_hit = await call_gemini(
                model=settings.rival_sentiment_model,
                prompt=current_prompt,
                config=types.GenerateContentConfig(
                    tools=[_GROUNDING_TOOL],
                    temperature=0.2,
                    max_output_tokens=1572,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            data = parse_json_response(response_text)
            result = SentimentResult(**data)

            log_tool_call(
                competitor_count=len(names),
                pain_point_count=len(result.pain_points),
                praised_feature_count=len(result.praised_features),
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
            )

            return ToolResult(
                success=True,
                fallback_used=fallback_used,
                data=result.model_dump(),
            )

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "SentimentAnalyzerTool attempt failed | attempt=%d error=%s",
                attempt + 1,
                last_error,
            )
            fallback_used = True

            if attempt == max_retries:
                log_tool_call(
                    competitor_count=len(names),
                    pain_point_count=0,
                    praised_feature_count=0,
                    grounding_hit=grounding_hit,
                    fallback_used=True,
                )
                return ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"error": f"Max retries reached: {last_error}"},
                )

        except Exception as exc:
            logger.exception(
                "Unexpected SentimentAnalyzerTool error | category=%s platform=%s",
                category,
                target_platform,
            )
            log_tool_call(
                competitor_count=len(names),
                pain_point_count=0,
                praised_feature_count=0,
                grounding_hit=grounding_hit,
                fallback_used=True,
            )
            return ToolResult(
                success=False, fallback_used=True, data={"error": str(exc)}
            )

    return ToolResult(
        success=False, fallback_used=True, data={"error": "Unexpected error"}
    )
