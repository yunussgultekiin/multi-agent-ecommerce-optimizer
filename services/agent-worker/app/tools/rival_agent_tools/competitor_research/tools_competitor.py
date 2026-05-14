import asyncio
import logging
from typing import Any
from google import genai
from google.genai import types
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from .models_competitor import (
    CompetitorResult,
    MAX_VALID_COMPETITORS,
    MIN_VALID_COMPETITORS,
    Platform,
    ProductDetailsResult,
    TrendResearchResult,
)
from .prompts_competitor import build_product_details_prompt, build_trends_prompt
from .utils_competitor import (
    extract_source_urls,
    log_research_summary,
    log_tool_call,
    parse_json_response,
)

logger = logging.getLogger(__name__)
_client = genai.Client(api_key=settings.gemini_api_key or None)
_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
SUPPORTED_PLATFORMS = {"amazon", "trendyol", "hepsiburada"}

def _normalize_platform(value: Any) -> Platform | None:
    if not isinstance(value, str): return None
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_PLATFORMS: return None
    return normalized

async def _call_gemini_with_grounding(prompt: str) -> tuple[str, list[str], bool]:
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: _client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[_GROUNDING_TOOL],
                response_mime_type="application/json",
                temperature=0.2,
            ),
        ),
    )

    source_urls = extract_source_urls(response)
    return response.text or "", source_urls, len(source_urls) > 0

async def _fetch_competitor_data(
    competitor_name: str,
    category: str,
    platform: Platform,
    product_url: str = "",
    correction_context: str | None = None,
) -> tuple[ProductDetailsResult, TrendResearchResult, list[str], bool]:
    product_prompt = build_product_details_prompt(
        competitor_name=competitor_name,
        platform=platform,
        product_url=product_url,
        correction_context=correction_context,
    )

    trends_prompt = build_trends_prompt(
        competitor_name=competitor_name,
        category=category,
        platform=platform,
        correction_context=correction_context,
    )

    product_response, trends_response = await asyncio.gather(
        _call_gemini_with_grounding(product_prompt),
        _call_gemini_with_grounding(trends_prompt),
    )

    product_text, product_sources, product_hit = product_response
    trends_text, trends_sources, trends_hit = trends_response

    product_data = parse_json_response(product_text)
    trends_data = parse_json_response(trends_text)

    product_result = ProductDetailsResult(**product_data)
    trends_result = TrendResearchResult(**trends_data)

    all_source_urls = list(dict.fromkeys(product_sources + trends_sources))

    return product_result, trends_result, all_source_urls, product_hit or trends_hit

def _merge_results(
    competitor_name: str,
    platform: Platform,
    product_url: str,
    product_result: ProductDetailsResult,
    trends_result: TrendResearchResult,
    source_urls: list[str],
) -> CompetitorResult:
    product_data = product_result.model_dump()
    trends_data = trends_result.model_dump()

    merged = {
        **product_data,
        **trends_data,
        "platform": platform,
        "source_urls": source_urls,
    }

    if not merged.get("competitor_name"):
        merged["competitor_name"] = competitor_name

    if not merged.get("product_url") and product_url:
        merged["product_url"] = product_url

    return CompetitorResult(**merged)

def _is_visual_ready_result(result: ToolResult) -> bool:
    return bool(
        result.success
        and result.data
        and result.data.get("image_urls")
    )

async def _research_one(
    competitor_name: str,
    category: str,
    platform: Platform,
    product_url: str = "",
    max_retries: int = 2,
) -> ToolResult:
    last_error: str | None = None
    fallback_used = False
    grounding_hit = False

    for attempt in range(max_retries + 1):
        correction_context = None

        if attempt > 0:
            correction_context = (
                f"Validation or JSON parsing failed in the previous attempt:\n"
                f"{last_error}\n\n"
                "Return ONLY valid JSON matching the requested schema. "
                "Use null for unavailable numeric fields. "
                "Use arrays for list fields. "
                "Use only real http/https URLs. "
                "Provide real product image URLs in image_urls when available."
            )
            fallback_used = True

        try:
            (
                product_result,
                trends_result,
                source_urls,
                grounding_hit,
            ) = await _fetch_competitor_data(
                competitor_name=competitor_name,
                category=category,
                platform=platform,
                product_url=product_url,
                correction_context=correction_context,
            )

            result = _merge_results(
                competitor_name=competitor_name,
                platform=platform,
                product_url=product_url,
                product_result=product_result,
                trends_result=trends_result,
                source_urls=source_urls,
            )

            if not result.image_urls:
                fallback_used = True
                logger.warning(
                    "Competitor research succeeded but no valid image_urls found | competitor=%s platform=%s",
                    competitor_name,
                    platform,
                )

            log_tool_call(
                competitor_name=competitor_name,
                platform=platform,
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
                visual_ready=bool(result.image_urls),
            )

            return ToolResult(
                success=True,
                data=result.model_dump(),
                fallback_used=fallback_used,
            )

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)

            logger.warning(
                "CompetitorResearchTool validation attempt failed | attempt=%d competitor=%s platform=%s error=%s",
                attempt + 1,
                competitor_name,
                platform,
                last_error,
            )

            if attempt == max_retries:
                log_tool_call(
                    competitor_name=competitor_name,
                    platform=platform,
                    grounding_hit=grounding_hit,
                    fallback_used=True,
                    visual_ready=False,
                )

                return ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"error": f"Max retries reached: {last_error}"},
                )

        except Exception as exc:
            logger.exception(
                "CompetitorResearchTool unexpected Gemini/tool error | competitor=%s platform=%s",
                competitor_name,
                platform,
            )

            log_tool_call(
                competitor_name=competitor_name,
                platform=platform,
                grounding_hit=grounding_hit,
                fallback_used=True,
                visual_ready=False,
            )

            return ToolResult(
                success=False,
                fallback_used=True,
                data={"error": str(exc)},
            )

    return ToolResult(
        success=False,
        fallback_used=True,
        data={"error": "Unexpected error"},
    )

def _extract_competitor_input(competitor: Any) -> tuple[str | None, Platform | None, str]:
    if not isinstance(competitor, dict):
        return None, None, ""

    competitor_name = (
        competitor.get("competitor_name")
        or competitor.get("name")
        or competitor.get("product_name")
    )

    if isinstance(competitor_name, str):
        competitor_name = competitor_name.strip()
    else:
        competitor_name = None

    platform = _normalize_platform(competitor.get("platform"))

    product_url = competitor.get("product_url") or ""

    if isinstance(product_url, str):
        product_url = product_url.strip()
    else:
        product_url = ""

    return competitor_name, platform, product_url

async def _research_from_input(
    competitor: Any,
    category: str,
) -> ToolResult:
    competitor_name, platform, product_url = _extract_competitor_input(competitor)

    if not competitor_name:
        return ToolResult(
            success=False,
            fallback_used=True,
            data={"error": "Invalid competitor input: missing competitor_name"},
        )

    if not platform:
        return ToolResult(
            success=False,
            fallback_used=True,
            data={"error": f"Invalid competitor input for {competitor_name}: missing or unsupported platform"},
        )

    return await _research_one(
        competitor_name=competitor_name,
        category=category,
        platform=platform,
        product_url=product_url,
    )

async def run_competitor_research_tool(
    competitors: list[dict],
    category: str,
) -> list[ToolResult]:
    if not isinstance(competitors, list):
        raise ValueError("competitors must be a list")

    category = (
        category.strip()
        if isinstance(category, str) and category.strip()
        else "general product category"
    )

    input_count = len(competitors)

    logger.info(
        "Researching %d competitors | category=%s | model=%s",
        input_count,
        category,
        settings.gemini_model,
    )

    if input_count < MIN_VALID_COMPETITORS:
        logger.warning(
            "CompetitorResearchTool received fewer competitors than minimum threshold | received=%d minimum=%d",
            input_count,
            MIN_VALID_COMPETITORS,
        )

    if input_count > MAX_VALID_COMPETITORS:
        logger.warning(
            "CompetitorResearchTool received more competitors than maximum threshold | received=%d maximum=%d. Extra competitors will be ignored.",
            input_count,
            MAX_VALID_COMPETITORS,
        )

    competitors = competitors[:MAX_VALID_COMPETITORS]

    results = await asyncio.gather(
        *[
            _research_from_input(
                competitor=competitor,
                category=category,
            )
            for competitor in competitors
        ],
        return_exceptions=True,
    )

    tool_results: list[ToolResult] = []

    for competitor, result in zip(competitors, results):
        competitor_name, platform, _ = _extract_competitor_input(competitor)

        if isinstance(result, Exception):
            logger.exception(
                "Unexpected competitor research error | competitor=%s platform=%s",
                competitor_name or "unknown",
                platform or "unknown",
            )

            tool_results.append(
                ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"error": str(result)},
                )
            )
        else:
            tool_results.append(result)

    successful_count = sum(1 for result in tool_results if result.success)
    visual_ready_count = sum(1 for result in tool_results if _is_visual_ready_result(result))

    workflow_fallback_used = (
        successful_count < MAX_VALID_COMPETITORS
        or visual_ready_count < MAX_VALID_COMPETITORS
    )

    if successful_count < MIN_VALID_COMPETITORS:
        logger.warning(
            "CompetitorResearchTool produced insufficient successful competitors | successful=%d minimum=%d",
            successful_count,
            MIN_VALID_COMPETITORS,
        )

    if visual_ready_count < MIN_VALID_COMPETITORS:
        logger.warning(
            "CompetitorResearchTool produced insufficient visual-ready competitors | visual_ready=%d minimum=%d",
            visual_ready_count,
            MIN_VALID_COMPETITORS,
        )

    log_research_summary(
        input_count=input_count,
        processed_count=len(tool_results),
        successful_count=successful_count,
        visual_ready_count=visual_ready_count,
        fallback_used=workflow_fallback_used,
    )

    return tool_results