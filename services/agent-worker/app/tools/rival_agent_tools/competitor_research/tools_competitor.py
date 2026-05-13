import asyncio
import json
import logging
from pydantic import ValidationError
from google import genai
from google.genai import types
from .models_competitor import CompetitorResult, ToolResult
from .prompts_competitor import build_product_details_prompt, build_trends_prompt
from .utils_competitor import extract_source_urls, clean_json_response, log_tool_call

logger = logging.getLogger(__name__)
_client = genai.Client()
_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())

async def _call_gemini_with_grounding(prompt: str) -> tuple[str, list[str], bool]:
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[_GROUNDING_TOOL]),
        ),
    )
    source_urls = extract_source_urls(response)
    return response.text, source_urls, len(source_urls) > 0

async def _fetch_competitor_data(
    competitor_name: str,
    category: str,
    product_url: str = "",
) -> tuple[dict, dict, list[str], bool]:
    product_prompt = build_product_details_prompt(competitor_name, product_url)
    trends_prompt = build_trends_prompt(competitor_name, category)

    (product_text, product_sources, product_hit), (trends_text, trends_sources, trends_hit) = await asyncio.gather(
        _call_gemini_with_grounding(product_prompt),
        _call_gemini_with_grounding(trends_prompt),
    )

    product_data = json.loads(clean_json_response(product_text))
    trends_data = json.loads(clean_json_response(trends_text))
    all_source_urls = list(set(product_sources + trends_sources))
    return product_data, trends_data, all_source_urls, product_hit or trends_hit

async def _research_one(
    competitor_name: str,
    category: str,
    product_url: str = "",
    max_retries: int = 2,
) -> ToolResult:
    last_error = None
    fallback_used = False

    for attempt in range(max_retries + 1):
        try:
            product_data, trends_data, source_urls, grounding_hit = await _fetch_competitor_data(
                competitor_name, category, product_url
            )
            merged = {**product_data, **trends_data, "source_urls": source_urls}
            result = CompetitorResult(**merged)
            log_tool_call(competitor_name=competitor_name, grounding_hit=grounding_hit, fallback_used=fallback_used)
            return ToolResult(success=True, data=result, fallback_used=fallback_used)

        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning("Attempt %d failed | competitor=%s error=%s", attempt + 1, competitor_name, last_error)
            fallback_used = True

            if attempt == max_retries:
                log_tool_call(competitor_name=competitor_name, grounding_hit=False, fallback_used=True)
                return ToolResult(success=False, fallback_used=True, error=f"Max retries reached: {last_error}")

    return ToolResult(success=False, fallback_used=True, error="Unexpected error")

async def run_competitor_research_tool(
    competitors: list[dict],
    category: str,
) -> list[ToolResult]:
    logger.info("Researching %d competitors | category=%s", len(competitors), category)

    results = await asyncio.gather(
        *[
            _research_one(c["competitor_name"], category, c.get("product_url", ""))
            for c in competitors
        ],
        return_exceptions=True,
    )

    tool_results = []
    for competitor, result in zip(competitors, results):
        if isinstance(result, Exception):
            logger.error("Unexpected error | competitor=%s error=%s", competitor["competitor_name"], result)
            tool_results.append(ToolResult(success=False, fallback_used=True, error=str(result)))
        else:
            tool_results.append(result)

    return tool_results
