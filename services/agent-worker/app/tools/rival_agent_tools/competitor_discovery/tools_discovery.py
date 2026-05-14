# services/agent-worker/app/tools/rival_agent_tools/competitor_discovery/tools_discovery.py

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
from .models_discovery import (
    DiscoveredCompetitor,
    DiscoveryResult,
    MAX_COMPETITORS,
    MIN_COMPETITORS,
    PLATFORM_DOMAINS,
    Platform,
    RawDiscoveryResult,
)
from .prompts_discovery import build_discovery_prompt, build_discovery_correction_context
from .utils_discovery import (
    build_grounded_product_url_candidates,
    choose_grounded_url_for_candidate,
    extract_source_urls,
    extract_trendyol_product_id,
    is_probably_valid_product_url,
    log_tool_call,
    normalize_url_for_compare,
    parse_json_response,
    resolve_grounding_source_urls,
)

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)

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

    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=settings.gemini_research_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[_GROUNDING_TOOL],
                    temperature=0.1,
                    max_output_tokens=1200,
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
    grounding_hit = len(source_urls) > 0

    return response.text or "", source_urls, grounding_hit


def _build_correction_context(last_error: str) -> str:
    return build_discovery_correction_context(last_error, MIN_COMPETITORS, MAX_COMPETITORS)


def _build_fallback_discovery_result(
    raw_result: RawDiscoveryResult,
    platform: Platform,
) -> DiscoveryResult:
    logger.warning(
        "Using fallback URL validation because grounding metadata is unavailable."
    )

    valid: list[DiscoveredCompetitor] = []
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    seen_pids: set[str] = set()

    rejected_url_count = 0
    duplicate_pid_count = 0

    for candidate in raw_result.competitors:
        candidate_platform = candidate.platform or platform

        if candidate_platform != platform:
            rejected_url_count += 1
            continue

        if not candidate.product_url:
            rejected_url_count += 1
            continue

        if not is_probably_valid_product_url(candidate.product_url, platform):
            rejected_url_count += 1
            continue

        normalized_url = normalize_url_for_compare(candidate.product_url)
        normalized_name = " ".join(candidate.competitor_name.strip().lower().split())

        if normalized_url in seen_urls:
            rejected_url_count += 1
            continue

        if normalized_name in seen_names:
            rejected_url_count += 1
            continue

        if platform == "trendyol":
            pid = extract_trendyol_product_id(candidate.product_url)

            if pid:
                if pid in seen_pids:
                    duplicate_pid_count += 1
                    rejected_url_count += 1
                    continue

                seen_pids.add(pid)

        seen_urls.add(normalized_url)
        seen_names.add(normalized_name)

        valid.append(
            DiscoveredCompetitor(
                competitor_name=candidate.competitor_name,
                product_url=candidate.product_url,
                platform=platform,
                source_url_index=candidate.source_url_index,
            )
        )

        if len(valid) >= MAX_COMPETITORS:
            break

    if len(valid) < MIN_COMPETITORS:
        raise ValueError(
            f"Only {len(valid)} fallback-validated competitors found "
            f"(rejected={rejected_url_count}, duplicate_product_ids={duplicate_pid_count}). "
            f"Minimum required is {MIN_COMPETITORS}."
        )

    return DiscoveryResult(
        competitors=valid[:MAX_COMPETITORS],
        source_urls=[],
        resolved_source_urls=[],
        rejected_url_count=rejected_url_count,
        duplicate_pid_count=duplicate_pid_count,
        rejected_ungrounded_url_count=0,
        source_index_used_count=0,
        fallback_source_pick_count=0,
    )


def _build_grounded_discovery_result(
    raw_result: RawDiscoveryResult,
    platform: Platform,
    source_urls: list[str],
    resolved_source_urls: list[str],
) -> DiscoveryResult:
    if not source_urls:
        return _build_fallback_discovery_result(
            raw_result=raw_result,
            platform=platform,
        )

    product_url_candidates = build_grounded_product_url_candidates(
        source_urls=source_urls,
        resolved_source_urls=resolved_source_urls,
        platform=platform,
    )

    if len(product_url_candidates) < MIN_COMPETITORS:
        logger.warning(
            "Insufficient grounded product URL candidates. Falling back to deterministic URL validation."
        )

        return _build_fallback_discovery_result(
            raw_result=raw_result,
            platform=platform,
        )

    valid: list[DiscoveredCompetitor] = []
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    seen_pids: set[str] = set()

    rejected_url_count = 0
    duplicate_pid_count = 0
    rejected_ungrounded_url_count = 0
    source_index_used_count = 0
    fallback_source_pick_count = 0

    for candidate in raw_result.competitors:
        candidate_platform = candidate.platform or platform

        if candidate_platform != platform:
            rejected_url_count += 1
            continue

        source_idx, grounded_url, used_requested_index = choose_grounded_url_for_candidate(
            source_url_index=candidate.source_url_index,
            product_url_candidates=product_url_candidates,
            used_normalized_urls=seen_urls,
        )

        if not grounded_url:
            rejected_ungrounded_url_count += 1
            continue

        if not is_probably_valid_product_url(grounded_url, platform):
            rejected_url_count += 1
            continue

        normalized_url = normalize_url_for_compare(grounded_url)
        normalized_name = " ".join(candidate.competitor_name.strip().lower().split())

        if normalized_url in seen_urls:
            rejected_url_count += 1
            continue

        if normalized_name in seen_names:
            rejected_url_count += 1
            continue

        if platform == "trendyol":
            pid = extract_trendyol_product_id(grounded_url)

            if pid:
                if pid in seen_pids:
                    duplicate_pid_count += 1
                    rejected_url_count += 1
                    continue

                seen_pids.add(pid)

        seen_urls.add(normalized_url)
        seen_names.add(normalized_name)

        if used_requested_index:
            source_index_used_count += 1
        else:
            fallback_source_pick_count += 1

        valid.append(
            DiscoveredCompetitor(
                competitor_name=candidate.competitor_name,
                product_url=grounded_url,
                platform=platform,
                source_url_index=source_idx,
            )
        )

        if len(valid) >= MAX_COMPETITORS:
            break

    if len(valid) < MIN_COMPETITORS:
        logger.warning(
            "Insufficient valid grounded competitors. Falling back to deterministic URL validation."
        )

        return _build_fallback_discovery_result(
            raw_result=raw_result,
            platform=platform,
        )

    return DiscoveryResult(
        competitors=valid[:MAX_COMPETITORS],
        source_urls=source_urls,
        resolved_source_urls=resolved_source_urls,
        rejected_url_count=rejected_url_count,
        duplicate_pid_count=duplicate_pid_count,
        rejected_ungrounded_url_count=rejected_ungrounded_url_count,
        source_index_used_count=source_index_used_count,
        fallback_source_pick_count=fallback_source_pick_count,
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
            response_text, source_urls, grounding_hit = await _call_gemini_with_grounding(prompt)

            if not grounding_hit or not source_urls:
                logger.warning(
                    "No grounding source URLs found. Falling back to deterministic URL validation."
                )

                source_urls = []
                resolved_source_urls = []
                fallback_used = True
            else:
                resolved_source_urls = await resolve_grounding_source_urls(source_urls)

            data = parse_json_response(response_text)
            raw_result = RawDiscoveryResult(**data)

            result = _build_grounded_discovery_result(
                raw_result=raw_result,
                platform=platform,
                source_urls=source_urls,
                resolved_source_urls=resolved_source_urls,
            )

            discovered_count = len(result.competitors)

            if discovered_count < MAX_COMPETITORS:
                fallback_used = True

            product_urls_from_grounding_metadata = bool(
                result.source_urls and result.resolved_source_urls
            )

            log_tool_call(
                platform=platform,
                category=category,
                discovered_count=discovered_count,
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
                valid_url_count=discovered_count,
                rejected_url_count=result.rejected_url_count,
                duplicate_pid_count=result.duplicate_pid_count,
                rejected_ungrounded_url_count=result.rejected_ungrounded_url_count,
                source_url_count=len(result.source_urls),
                resolved_source_url_count=len(result.resolved_source_urls),
                source_index_used_count=result.source_index_used_count,
                fallback_source_pick_count=result.fallback_source_pick_count,
            )

            result_data = result.model_dump()
            result_data["_meta"] = {
                "valid_url_count": discovered_count,
                "rejected_url_count": result.rejected_url_count,
                "duplicate_pid_count": result.duplicate_pid_count,
                "rejected_ungrounded_url_count": result.rejected_ungrounded_url_count,
                "source_url_count": len(result.source_urls),
                "resolved_source_url_count": len(result.resolved_source_urls),
                "source_index_used_count": result.source_index_used_count,
                "fallback_source_pick_count": result.fallback_source_pick_count,
                "product_urls_from_grounding_metadata": product_urls_from_grounding_metadata,
                "fallback_url_validation": not product_urls_from_grounding_metadata,
            }

            return ToolResult(
                success=True,
                data=result_data,
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