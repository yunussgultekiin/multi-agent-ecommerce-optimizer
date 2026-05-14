import asyncio
import logging
from google import genai
from google.genai import types
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from .models_discovery import (
    DiscoveryResult,
    MAX_COMPETITORS,
    MIN_COMPETITORS,
    PLATFORM_DOMAINS,
    Platform,
)
from .prompts_discovery import build_discovery_prompt
from .utils_discovery import extract_source_urls, log_tool_call, parse_json_response

logger = logging.getLogger(__name__)
_client = genai.Client(api_key=settings.gemini_api_key or None)
_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
SUPPORTED_PLATFORMS = set(PLATFORM_DOMAINS.keys())

def _validate_platform(platform: str) -> Platform:
    normalized = platform.strip().lower() if isinstance(platform, str) else ""
    if normalized not in SUPPORTED_PLATFORMS:
        raise ValueError(
            f"Unsupported platform: {platform}. Supported platforms: {sorted(SUPPORTED_PLATFORMS)}"
        )

    return normalized 

def _normalize_text(value: str, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()

    return fallback

async def _call_gemini_with_grounding(prompt: str):
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
    grounding_hit = len(source_urls) > 0
    return response.text or "", source_urls, grounding_hit

def _build_correction_context(last_error: str) -> str:
    return (
        f"Validation or JSON parsing failed with this error:\n"
        f"{last_error}\n\n"
        "Return ONLY valid JSON matching the requested schema. "
        f"Return between {MIN_COMPETITORS} and {MAX_COMPETITORS} unique competitors. "
        "Each competitor must have competitor_name, product_url, and platform. "
        "product_url must be a valid product detail page URL on the selected platform. "
        "Do not include duplicate products. "
        "Do not include the user's own brand."
    )

async def run_competitor_discovery_tool(
    platform: str,
    category: str,
    product_title: str,
    brand: str,
    max_retries: int = 2,
) -> ToolResult:
    try:
        platform = _validate_platform(platform)
    except ValueError as exc:
        return ToolResult(
            success=False,
            fallback_used=True,
            data={"error": str(exc)},
        )

    category = _normalize_text(category, "general product category")
    product_title = _normalize_text(product_title, "user product")
    brand = brand.strip() if isinstance(brand, str) else ""

    last_error: str | None = None
    fallback_used = False
    grounding_hit = False

    for attempt in range(max_retries + 1):
        correction_context = None

        if attempt > 0 and last_error:
            correction_context = _build_correction_context(last_error)
            fallback_used = True

        prompt = build_discovery_prompt(
            platform=platform,
            category=category,
            product_title=product_title,
            brand=brand,
            correction_context=correction_context,
        )

        try:
            response_text, source_urls, grounding_hit = await _call_gemini_with_grounding(
                prompt
            )

            data = parse_json_response(response_text)

            result = DiscoveryResult(
                source_urls=source_urls,
                **data,
            )

            discovered_count = len(result.competitors)

            if discovered_count < MIN_COMPETITORS:
                raise ValueError(
                    f"Only {discovered_count} valid competitors found. Minimum required is {MIN_COMPETITORS}."
                )

            if discovered_count < MAX_COMPETITORS:
                fallback_used = True

            log_tool_call(
                platform=platform,
                category=category,
                discovered_count=discovered_count,
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
                "Discovery attempt failed | attempt=%d platform=%s category=%s error=%s",
                attempt + 1,
                platform,
                category,
                last_error,
            )

            fallback_used = True

            if attempt == max_retries:
                log_tool_call(
                    platform=platform,
                    category=category,
                    discovered_count=0,
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
                "Unexpected CompetitorDiscoveryTool error | platform=%s category=%s",
                platform,
                category,
            )

            log_tool_call(
                platform=platform,
                category=category,
                discovered_count=0,
                grounding_hit=grounding_hit,
                fallback_used=True,
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