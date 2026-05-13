import asyncio
import json
import logging
import httpx
from pydantic import ValidationError
import google.generativeai as genai
from app.config import settings
from .models_synthesis import ImageAnalysisResult
from .prompts_synthesis import build_synthesis_prompt
from .utils_synthesis import fetch_image_as_base64, clean_json_response

logger = logging.getLogger(__name__)

async def _analyze_single_image(url: str, client: httpx.AsyncClient, is_competitor: bool = False) -> dict:
    image_data = await fetch_image_as_base64(url, client)
    label = "rival product image" if is_competitor else "user product image"
    model = genai.GenerativeModel(settings.gemini_model)
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: model.generate_content([
            f"This is a {label}. Analyze it in terms of composition, colors, background, and product focus.",
            {"mime_type": image_data["mime_type"], "data": image_data["data"]},
        ]),
    )
    return {"url": url, "is_competitor": is_competitor, "raw_analysis": response.text}

async def _analyze_all_images(
    user_image_urls: list[str],
    competitor_image_urls: list[str],
) -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [
            *[_analyze_single_image(url, client, is_competitor=False) for url in user_image_urls],
            *[_analyze_single_image(url, client, is_competitor=True) for url in competitor_image_urls],
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    valid = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]
    if failed:
        logger.warning("%d images could not be processed: %s", len(failed), failed)
    return valid

async def _generate_structured_analysis(
    all_analyses: list[dict],
    variants: list[dict] | None = None,
    max_retries: int = 2,
) -> ImageAnalysisResult:
    model = genai.GenerativeModel(settings.gemini_model)
    loop = asyncio.get_running_loop()
    user_analyses = [a for a in all_analyses if not a["is_competitor"]]
    competitor_analyses = [a for a in all_analyses if a["is_competitor"]]
    prompt = build_synthesis_prompt(user_analyses, competitor_analyses, variants)
    last_error = None

    for attempt in range(max_retries + 1):
        current_prompt = prompt
        if attempt > 0:
            correction_context = (
                f"THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:\n{last_error}\n\n"
                "Fix these errors and return ONLY valid JSON.\n"
                "Pay special attention to:\n"
                "- product_focus_score and quality_score must be between 0.0 and 1.0\n"
                "- dominant_colors must contain at least 1 item\n"
                "- generation_prompt must be at least 20 characters long\n\n"
                "Original task:\n"
            )
            current_prompt = correction_context + prompt

        response = await loop.run_in_executor(
            None,
            lambda p=current_prompt: model.generate_content(p),
        )

        try:
            cleaned = clean_json_response(response.text)
            data = json.loads(cleaned)
            result = ImageAnalysisResult(**data)
            logger.info("Vision synthesis succeeded on attempt %d", attempt + 1)
            return result
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning("Vision synthesis attempt %d failed: %s", attempt + 1, last_error)
            if attempt == max_retries:
                raise ValueError(f"Max retries reached. Last error: {last_error}")

    raise ValueError("Unexpected error in vision synthesis")

async def run_vision_synthesis_tool(
    user_image_urls: list[str],
    competitor_image_urls: list[str],
    variants: list[dict] | None = None,
) -> ImageAnalysisResult:
    logger.info(
        "Analyzing %d user images + %d competitor images",
        len(user_image_urls),
        len(competitor_image_urls),
    )
    all_analyses = await _analyze_all_images(user_image_urls, competitor_image_urls)
    return await _generate_structured_analysis(all_analyses, variants=variants)
