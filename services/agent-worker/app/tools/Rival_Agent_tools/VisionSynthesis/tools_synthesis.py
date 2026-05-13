import asyncio
import json
import logging

import httpx
from pydantic import ValidationError
import google.generativeai as genai

from .models_synthesis import ImageAnalysisResult
from .prompts_synthesis import build_synthesis_prompt
from .utils_synthesis import fetch_image_as_base64, clean_json_response

logger = logging.getLogger(__name__)

async def analyze_singe_image(
    url: str,
    client: httpx.AsyncClient,
    is_competitor: bool = False
) -> dict:
    image_data = await fetch_image_as_base64(url,client)
    label = "rivals products image" if is_competitor else "user product image"

    model = genai.GenerativeModel("gemini-1.5-flash")
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: model.generate_content([
            f"This is a {label}. Analyze it in terms of composition, colors, background, and product focus.",
            {"mime_type": image_data["mime_type"], "data": image_data["data"]}
        ])
    )

    return {
        "url": url,
        "is_competitor": is_competitor,
        "raw_analysis": response.text
    }

async def analyze_all_images(
    user_image_urls: list[str],
    competitor_image_urls: list[str]
) -> list[dict]:
    async with httpx.AsyncClient() as client:
        user_tasks = [
            analyze_singe_image(url, client, is_competitor = False)
            for url in user_image_urls
        ]
        competitor_tasks = [
            analyze_singe_image(url, client, is_competitor = True)
            for url in competitor_image_urls
        ]

        results = await asyncio.gather(
            *user_tasks,
            *competitor_tasks,
            return_exceptions = True
        )
    
    valid_results = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]

    if failed:
        logger.warning(f"{len(failed)} image couldnt processed: {failed}")

    return valid_results

async def generate_structured_analysis(
    all_analyses: list[dict],
    max_retries: int = 2
) -> ImageAnalysisResult:
    model = genai.GenerativeModel("gemini-1.5-flash")
    loop = asyncio.get_running_loop()

    user_analyses = [a for a in all_analyses if not a["is_competitor"]]
    competitor_analyses = [a for a in all_analyses if a["is_competitor"]]

    prompt = build_synthesis_prompt(user_analyses, competitor_analyses)
    last_error = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            correction_context = f"""
            THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
            {last_error}

            Fix these errors and return ONLY valid JSON.
            Pay special attention to:
            - product_focus_score and quality_score must be between 0.0 and 1.0
            - dominant_colors must contain at least 1 item
            - generation_prompt must be at least 50 characters long
            """
            current_prompt = correction_context + "\n\n Original task: \n" + prompt
        else:
            current_prompt = prompt
        
        response = await loop.run_in_executor(
            None,
            lambda p = current_prompt: model.generate_content(p)
        )

        try:
            cleaned = clean_json_response(response.text)
            data = json.loads(cleaned)
            result = ImageAnalysisResult(**data)

            logger.info(f"Successful on attempt {attempt + 1}.")
            return result

        except(ValidationError,json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed: {last_error}")

            if attempt == max_retries:
                raise ValueError(f"Maximum number of attempts reached. Last error: {last_error}")
    
    raise ValueError("Unexpected error.")

async def run_vision_synthesis_tool(
    user_image_urls: list[str],
    competitor_image_urls: list[str]
) -> ImageAnalysisResult:
    logger.info(
        f"Analyzing {len(user_image_urls)} user images + "
        f"{len(competitor_image_urls)} competitor images..."
    )

    all_analyses = await analyze_all_images(user_image_urls,competitor_image_urls)
    result = await generate_structured_analysis(all_analyses)

    return result