# services/agent-worker/app/tools/rival_agent_tools/competitor_research/tools_competitor.py

import asyncio
import logging
from typing import Any
import google.auth.exceptions
import google.api_core.exceptions
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from .models_competitor import (
    CompetitorResult,
    MAX_VALID_COMPETITORS,
    MIN_VALID_COMPETITORS,
    Platform,
)
from .prompts_competitor import build_competitor_prompt
from .utils_competitor import (
    extract_cdn_images_from_sources,
    extract_source_urls,
    filter_image_urls,
    log_research_summary,
    log_tool_call,
    merge_image_urls,
    parse_json_response,
)

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)

_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())

try:
    _URL_CONTEXT_TOOL = types.Tool(url_context=types.UrlContext())
except TypeError:
    # Some google-genai versions expose UrlContext as a class token instead of an instance.
    _URL_CONTEXT_TOOL = types.Tool(url_context=types.UrlContext)

SUPPORTED_PLATFORMS = {"amazon", "trendyol", "hepsiburada"}


def _normalize_platform(value: Any) -> Platform | None:
    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()

    if normalized not in SUPPORTED_PLATFORMS:
        return None

    return normalized


def _extract_url_context_urls(response: Any) -> list[str]:
    urls: list[str] = []

    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        metadata = getattr(candidate, "url_context_metadata", None)

        if not metadata:
            continue

        url_metadata = getattr(metadata, "url_metadata", None) or getattr(metadata, "urlMetadata", None) or []

        for item in url_metadata:
            retrieved_url = (
                getattr(item, "retrieved_url", None)
                or getattr(item, "retrievedUrl", None)
                or getattr(item, "url", None)
            )

            if isinstance(retrieved_url, str) and retrieved_url.startswith(("http://", "https://")):
                urls.append(retrieved_url)

    return list(dict.fromkeys(urls))


async def _call_gemini(
    prompt: str,
    max_output_tokens: int = 1200,
    use_url_context: bool = False,
) -> tuple[str, list[str], bool, str]:
    loop = asyncio.get_running_loop()

    tool = _URL_CONTEXT_TOOL if use_url_context else _SEARCH_TOOL
    tool_mode = "url_context" if use_url_context else "google_search"

    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=settings.gemini_research_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[tool],
                    temperature=0.1 if use_url_context else 0.2,
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
            f"Model '{settings.gemini_research_model}' not found in region '{settings.google_cloud_location}'. "
            "Check the model name and location."
        ) from exc
    except google.api_core.exceptions.PermissionDenied as exc:
        raise RuntimeError(
            f"Permission denied. Ensure the account has the 'Vertex AI User' role "
            f"in project '{settings.google_cloud_project}'."
        ) from exc

    source_urls = extract_source_urls(response)

    if use_url_context:
        source_urls = list(dict.fromkeys([*source_urls, *_extract_url_context_urls(response)]))

    grounding_hit = len(source_urls) > 0

    return response.text or "", source_urls, grounding_hit, tool_mode


async def _fetch_competitor_data(
    competitor_name: str,
    category: str,
    platform: Platform,
    product_url: str = "",
    correction_context: str | None = None,
    max_output_tokens: int = 1200,
    use_url_context: bool = False,
) -> tuple[CompetitorResult, list[str], bool, str]:
    prompt = build_competitor_prompt(
        competitor_name=competitor_name,
        category=category,
        platform=platform,
        product_url=product_url,
        correction_context=correction_context,
        use_url_context=use_url_context,
    )

    response_text, source_urls, grounding_hit, tool_mode = await _call_gemini(
        prompt,
        max_output_tokens=max_output_tokens,
        use_url_context=use_url_context,
    )

    data = parse_json_response(response_text)

    data["platform"] = platform
    data["source_urls"] = source_urls

    if not data.get("competitor_name"):
        data["competitor_name"] = competitor_name

    if product_url:
        data["product_url"] = product_url

    return CompetitorResult(**data), source_urls, grounding_hit, tool_mode


def _is_visual_ready_result(result: ToolResult) -> bool:
    return bool(
        result.success
        and result.data
        and result.data.get("image_urls")
    )


def _resolve_image_source(
    source_image_count: int,
    gemini_image_count: int,
    final_image_count: int,
    tool_mode: str,
) -> str:
    if final_image_count == 0:
        return "none"

    if source_image_count > 0 and gemini_image_count > 0:
        return f"mixed_{tool_mode}"

    if source_image_count > 0:
        return f"{tool_mode}_source"

    return tool_mode


async def _research_one(
    competitor_name: str,
    category: str,
    platform: Platform,
    product_url: str = "",
    max_retries: int = 1,
) -> ToolResult:
    last_error: str | None = None
    grounding_hit = False

    # First try URL Context when we have a real product page URL.
    # If URL Context fails structurally, retry with Google Search grounding.
    planned_modes = [True, False] if product_url else [False]

    for mode_index, use_url_context in enumerate(planned_modes):
        for attempt in range(max_retries + 1):
            correction_context = None
            retrying = attempt > 0
            tool_retrying = mode_index > 0

            if retrying:
                correction_context = (
                    f"Validation or JSON parsing failed in the previous attempt:\n"
                    f"{last_error}\n\n"
                    "Return ONLY valid JSON matching the requested schema. "
                    "Use null for unavailable numeric fields. "
                    "Use arrays for list fields. "
                    "Use only real http/https URLs. "
                    "If product image URLs are unavailable, return image_urls=[]."
                )

            try:
                result, source_urls, grounding_hit, tool_mode = await _fetch_competitor_data(
                    competitor_name=competitor_name,
                    category=category,
                    platform=platform,
                    product_url=product_url,
                    correction_context=correction_context,
                    max_output_tokens=800 if retrying else 1200,
                    use_url_context=use_url_context,
                )

                gemini_image_count = len(result.image_urls)
                source_images = extract_cdn_images_from_sources(source_urls, platform)
                source_image_count = len(source_images)

                validated_gemini_images = filter_image_urls(result.image_urls, platform)
                final_images = merge_image_urls(
                    source_image_urls=source_images,
                    gemini_image_urls=validated_gemini_images,
                    platform=platform,
                )

                final_image_count = len(final_images)
                image_source = _resolve_image_source(
                    source_image_count=source_image_count,
                    gemini_image_count=len(validated_gemini_images),
                    final_image_count=final_image_count,
                    tool_mode=tool_mode,
                )

                fallback_used = retrying or tool_retrying or final_image_count == 0

                if final_image_count < gemini_image_count:
                    logger.info(
                        "Image URL validation rejected %d/%d Gemini images | competitor=%s platform=%s tool=%s",
                        gemini_image_count - len(validated_gemini_images),
                        gemini_image_count,
                        competitor_name,
                        platform,
                        tool_mode,
                    )

                if not final_images:
                    logger.info(
                        "Competitor research completed without product image URLs | competitor=%s platform=%s tool=%s",
                        competitor_name,
                        platform,
                        tool_mode,
                    )

                result_data = result.model_dump()
                result_data["image_urls"] = final_images
                result_data["_meta"] = {
                    "tool_mode": tool_mode,
                    "gemini_image_count": gemini_image_count,
                    "source_image_count": source_image_count,
                    "final_image_count": final_image_count,
                    "image_source": image_source,
                    "grounding_hit": grounding_hit,
                    "visual_ready": bool(final_images),
                    "url_context_used": use_url_context,
                    "search_fallback_used": tool_retrying,
                }

                log_tool_call(
                    competitor_name=competitor_name,
                    platform=platform,
                    grounding_hit=grounding_hit,
                    fallback_used=fallback_used,
                    visual_ready=bool(final_images),
                    gemini_image_count=gemini_image_count,
                    source_image_count=source_image_count,
                    final_image_count=final_image_count,
                    image_source=image_source,
                )

                return ToolResult(
                    success=True,
                    data=result_data,
                    fallback_used=fallback_used,
                )

            except (ValidationError, ValueError) as exc:
                last_error = str(exc)

                logger.warning(
                    "CompetitorResearchTool validation attempt failed | attempt=%d competitor=%s platform=%s url_context=%s error=%s",
                    attempt + 1,
                    competitor_name,
                    platform,
                    use_url_context,
                    last_error,
                )

                if attempt == max_retries:
                    break

            except Exception as exc:
                last_error = str(exc)

                logger.warning(
                    "CompetitorResearchTool tool mode failed | competitor=%s platform=%s url_context=%s error=%s",
                    competitor_name,
                    platform,
                    use_url_context,
                    last_error,
                )

                break

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
        data={"error": f"All research modes failed: {last_error or 'unknown error'}"},
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
        settings.gemini_research_model,
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

    workflow_fallback_used = successful_count < len(tool_results)

    if successful_count < MIN_VALID_COMPETITORS:
        logger.warning(
            "CompetitorResearchTool produced insufficient successful competitors | successful=%d minimum=%d",
            successful_count,
            MIN_VALID_COMPETITORS,
        )

    if visual_ready_count < MIN_VALID_COMPETITORS:
        logger.info(
            "CompetitorResearchTool completed with limited visual evidence | visual_ready=%d minimum=%d",
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