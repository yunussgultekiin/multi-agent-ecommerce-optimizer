import asyncio
import json
import logging
from typing import Any
import google.generativeai as genai
import httpx
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from .models_synthesis import ImageAnalysisResult, SynthesisMode
from .prompts_synthesis import build_synthesis_prompt
from .utils_synthesis import clean_json_response, fetch_image_as_base64, normalize_image_url

logger = logging.getLogger(__name__)
MIN_VALID_COMPETITOR_IMAGES = 3
MAX_COMPETITOR_IMAGES = 5
MAX_CONCURRENT_IMAGE_ANALYSES = 5

def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)

def _is_successful_tool_result(result: Any) -> bool:
    has_success_field = (
        isinstance(result, dict) and "success" in result
    ) or hasattr(result, "success")
    if not has_success_field: return True
    return bool(_get_value(result, "success", False))

def _extract_result_data(result: Any) -> Any:
    has_success_field = (
        isinstance(result, dict) and "success" in result
    ) or hasattr(result, "success")
    if has_success_field: return _get_value(result, "data")
    return result

def _extract_image_urls_from_data(data: Any) -> list[str]:
    if data is None: return []
    image_urls = _get_value(data, "image_urls", [])
    if not isinstance(image_urls, list): return []
    normalized_urls: list[str] = []

    for url in image_urls:
        normalized = normalize_image_url(url)

        if normalized:
            normalized_urls.append(normalized)

    return list(dict.fromkeys(normalized_urls))

def extract_valid_competitor_image_urls(
    competitor_research_results: list[Any],
    max_images: int = MAX_COMPETITOR_IMAGES,
) -> list[str]:
    """
    Extracts image URLs only from successful CompetitorResearchTool results.

    Rules:
    - Include only ToolResult(success=True)
    - Ignore failed results and data=None
    - Require data.image_urls[]
    - Use at most 1 image URL per competitor for diversity
    - Deduplicate URLs
    - Return max 5 URLs
    """
    selected_urls: list[str] = []
    seen_urls: set[str] = set()

    for result in competitor_research_results:
        if len(selected_urls) >= max_images: break

        if not _is_successful_tool_result(result): continue

        data = _extract_result_data(result)
        if data is None: continue

        image_urls = _extract_image_urls_from_data(data)
        if not image_urls: continue

        for url in image_urls:
            if url in seen_urls: continue
            selected_urls.append(url)
            seen_urls.add(url)
            break

    return selected_urls[:max_images]

def determine_synthesis_mode(valid_competitor_image_count: int) -> SynthesisMode:
    if valid_competitor_image_count >= MAX_COMPETITOR_IMAGES:
        return "competitor_supported"

    if valid_competitor_image_count >= MIN_VALID_COMPETITOR_IMAGES:
        return "partial_competitor_supported"

    return "fallback_user_product_only"

async def _analyze_single_image(
    url: str,
    client: httpx.AsyncClient,
    is_competitor: bool = True,
) -> dict:
    image_data = await fetch_image_as_base64(url, client)
    label = "rival product image" if is_competitor else "user product image"
    model = genai.GenerativeModel(settings.gemini_model)
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: model.generate_content(
            [
                (
                    f"This is a {label}. Analyze it for e-commerce product image style. "
                    "Focus on composition, dominant colors, background type, background removal, "
                    "lighting, soft shadows, camera angle, product framing, crop, product focus, "
                    "sharpness, visual quality, and premium marketplace presentation. "
                    "Do not describe how to redesign the product itself; focus only on visual presentation patterns."
                ),
                {
                    "mime_type": image_data["mime_type"],
                    "data": image_data["data"],
                },
            ]
        ),
    )

    return {
        "url": url,
        "is_competitor": is_competitor,
        "raw_analysis": response.text,
    }

async def _analyze_competitor_images(
    competitor_image_urls: list[str],
    max_concurrency: int = MAX_CONCURRENT_IMAGE_ANALYSES,
) -> list[dict]:
    if not competitor_image_urls: return []
    semaphore = asyncio.Semaphore(max_concurrency)

    async with httpx.AsyncClient() as client:
        async def limited_analyze(url: str) -> dict:
            async with semaphore:
                return await _analyze_single_image(
                    url=url,
                    client=client,
                    is_competitor=True,
                )

        tasks = [limited_analyze(url) for url in competitor_image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    valid = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]

    if failed:
        logger.warning(
            "%d competitor images could not be processed: %s",
            len(failed),
            failed,
        )

    return valid

async def _generate_structured_analysis(
    user_product: dict,
    competitor_analyses: list[dict],
    synthesis_mode: SynthesisMode,
    valid_competitor_image_count: int,
    max_retries: int = 2,
) -> ImageAnalysisResult:
    model = genai.GenerativeModel(settings.gemini_model)
    loop = asyncio.get_running_loop()

    prompt = build_synthesis_prompt(
        user_product=user_product,
        competitor_analyses=competitor_analyses,
        synthesis_mode=synthesis_mode,
        valid_competitor_image_count=valid_competitor_image_count,
    )

    last_error = None

    for attempt in range(max_retries + 1):
        current_prompt = prompt

        if attempt > 0:
            correction_context = (
                f"THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:\n"
                f"{last_error}\n\n"
                "Fix these errors and return ONLY valid JSON.\n"
                "Pay special attention to:\n"
                "- product_focus_score and quality_score must be between 0.0 and 1.0\n"
                "- dominant_colors must contain at least 1 item and use valid hex or named colors\n"
                "- generation_prompt must be between 20 and 500 characters\n"
                '- generation_prompt must start with "Edit the provided product image into"\n'
                "- generation_prompt must be an image editing instruction, not a from-scratch generation prompt\n"
                "- generation_prompt must preserve the exact product identity, shape, color, material, texture, proportions, and distinctive details\n"
                "- generation_prompt must not add new parts, accessories, labels, patterns, logos, features, or colors not present in user_product\n"
                "- generation_prompt must only improve presentation style such as background, lighting, shadow, crop, framing, sharpness, and e-commerce polish\n\n"
                "Original task:\n"
            )
            current_prompt = correction_context + prompt

        response = await loop.run_in_executor(
            None,
            lambda p=current_prompt: model.generate_content(
                p,
                generation_config={
                    "response_mime_type": "application/json",
                },
            ),
        )

        try:
            cleaned = clean_json_response(response.text)
            data = json.loads(cleaned)

            result = ImageAnalysisResult(**data)

            result = result.model_copy(
                update={
                    "synthesis_mode": synthesis_mode,
                    "valid_competitor_image_count": valid_competitor_image_count,
                    "fallback_used": synthesis_mode != "competitor_supported",
                }
            )

            logger.info(
                "Vision synthesis succeeded | attempt=%d mode=%s valid_images=%d fallback_used=%s",
                attempt + 1,
                synthesis_mode,
                valid_competitor_image_count,
                result.fallback_used,
            )

            return result

        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)

            logger.warning(
                "Vision synthesis attempt %d failed: %s",
                attempt + 1,
                last_error,
            )

            if attempt == max_retries:
                raise ValueError(
                    f"Max retries reached. Last error: {last_error}"
                ) from exc

    raise ValueError("Unexpected error in vision synthesis")

async def run_vision_synthesis_tool(
    user_product: dict,
    competitor_research_results: list[Any],
) -> ToolResult:
    try:
        if not isinstance(user_product, dict) or not user_product:
            return ToolResult(
                success=False,
                fallback_used=True,
                data={"error": "user_product must be a non-empty dictionary"},
            )

        if not isinstance(competitor_research_results, list):
            return ToolResult(
                success=False,
                fallback_used=True,
                data={"error": "competitor_research_results must be a list"},
            )

        competitor_image_urls = extract_valid_competitor_image_urls(
            competitor_research_results=competitor_research_results,
            max_images=MAX_COMPETITOR_IMAGES,
        )

        extracted_image_count = len(competitor_image_urls)

        logger.info(
            "VisionSynthesisTool extracted %d valid competitor image URLs from research results",
            extracted_image_count,
        )

        competitor_analyses: list[dict] = []

        if extracted_image_count >= MIN_VALID_COMPETITOR_IMAGES:
            competitor_analyses = await _analyze_competitor_images(
                competitor_image_urls=competitor_image_urls,
            )
        else:
            logger.warning(
                "Insufficient valid competitor image URLs for competitor-supported synthesis | extracted=%d minimum=%d",
                extracted_image_count,
                MIN_VALID_COMPETITOR_IMAGES,
            )

        analyzed_image_count = len(competitor_analyses)

        if analyzed_image_count < MIN_VALID_COMPETITOR_IMAGES:
            synthesis_mode: SynthesisMode = "fallback_user_product_only"
            competitor_analyses = []

            logger.warning(
                "Insufficient successfully analyzed competitor images. Falling back to user_product-only style brief | analyzed=%d minimum=%d",
                analyzed_image_count,
                MIN_VALID_COMPETITOR_IMAGES,
            )
        else:
            synthesis_mode = determine_synthesis_mode(analyzed_image_count)

        analysis = await _generate_structured_analysis(
            user_product=user_product,
            competitor_analyses=competitor_analyses,
            synthesis_mode=synthesis_mode,
            valid_competitor_image_count=analyzed_image_count,
        )

        return ToolResult(
            success=True,
            data=analysis.model_dump(),
            fallback_used=analysis.fallback_used,
        )

    except Exception as exc:
        logger.exception("VisionSynthesisTool unexpected error")
        return ToolResult(
            success=False,
            fallback_used=True,
            data={"error": str(exc)},
        )