from .models_discovery import (
    MIN_COMPETITORS,
    PLATFORM_SITES,
    TARGET_COMPETITORS,
    DiscoveredCompetitor,
    DiscoveryResult,
    Platform,
    RawDiscoveryResult,
)
from .prompts_discovery import (
    build_discovery_correction_context,
    build_discovery_prompt,
)
from .utils_discovery import log_tool_call, parse_json_response
from app.config import settings
from app.core import ToolResult
from app.gemini_client import call_gemini
from google.genai import types
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)
_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
SUPPORTED_PLATFORMS = set(PLATFORM_SITES.keys())

def _build_discovery_gemini_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[_GROUNDING_TOOL],
        temperature=0.1,
        max_output_tokens=2048,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

def _validate_platform(platform: str) -> Platform:
    normalized = platform.strip().lower() if isinstance(platform, str) else ""
    if normalized not in SUPPORTED_PLATFORMS:
        raise ValueError(
            f"Unsupported platform: {platform!r}. Supported: {sorted(SUPPORTED_PLATFORMS)}"
        )
    return normalized

def _deduplicate(competitors: list[DiscoveredCompetitor]) -> list[DiscoveredCompetitor]:
    seen: set[str] = set()
    result: list[DiscoveredCompetitor] = []
    for c in competitors:
        key = " ".join(c.competitor_name.lower().split())
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result

def _filter_own_brand(
    competitors: list[DiscoveredCompetitor],
    brand: str,
) -> list[DiscoveredCompetitor]:
    if not brand:
        return competitors
    brand_lower = brand.strip().lower()
    return [c for c in competitors if brand_lower not in c.competitor_name.lower()]

async def run_competitor_discovery_tool(
    platform: str,
    category: str,
    product_title: str,
    brand: str,
    max_retries: int = 2,
    exclude_names: list[str] | None = None,
) -> ToolResult:
    try:
        platform = _validate_platform(platform)
    except ValueError as exc:
        return ToolResult(success=False, fallback_used=True, data={"error": str(exc)})

    category = (
        category.strip()
        if isinstance(category, str) and category.strip()
        else "general"
    )
    product_title = (
        product_title.strip()
        if isinstance(product_title, str) and product_title.strip()
        else "user product"
    )
    brand = brand.strip() if isinstance(brand, str) else ""

    last_error: str | None = None
    fallback_used = False
    grounding_hit = False

    for attempt in range(max_retries + 1):
        correction_context = (
            build_discovery_correction_context(last_error)
            if attempt > 0 and last_error
            else None
        )
        if attempt > 0:
            fallback_used = True

        prompt = build_discovery_prompt(
            platform=platform,
            category=category,
            product_title=product_title,
            brand=brand,
            correction_context=correction_context,
            exclude_names=exclude_names,
        )

        try:
            response_text, grounding_hit = await call_gemini(
                model=settings.gemini_flash_model,
                prompt=prompt,
                config=_build_discovery_gemini_config(),
            )
            data = parse_json_response(response_text)
            raw_result = RawDiscoveryResult(**data)

            candidates = _filter_own_brand(
                _deduplicate(raw_result.competitors),
                brand,
            )

            discovered_count = len(candidates)

            if discovered_count < MIN_COMPETITORS:
                raise ValueError(
                    f"Only {discovered_count} valid competitors found "
                    f"(minimum {MIN_COMPETITORS} required)."
                )

            success = discovered_count >= TARGET_COMPETITORS
            if not success:
                fallback_used = True

            result = DiscoveryResult(competitors=candidates[:TARGET_COMPETITORS])

            log_tool_call(
                platform=platform,
                category=category,
                discovered_count=len(result.competitors),
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
            )

            return ToolResult(
                success=True,
                fallback_used=fallback_used,
                data={"competitors": [c.model_dump() for c in result.competitors]},
            )

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "CompetitorDiscoveryTool attempt failed | attempt=%d platform=%s error=%s",
                attempt + 1,
                platform,
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
                success=False, fallback_used=True, data={"error": str(exc)}
            )

    return ToolResult(
        success=False, fallback_used=True, data={"error": "Unexpected error"}
    )
