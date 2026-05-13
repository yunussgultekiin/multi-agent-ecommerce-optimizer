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

client = genai.Client()

GROUNDING_TOOL = types.Tool(
    google_search = types.GoogleSearch()
)

async def call_gemini_with_grounding(prompt: str) -> tuple[str, list[str], bool]:
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model = "gemini-2.0-flash",
            contents = prompt,
            config = types.GenerateContentConfig(
                tools = [GROUNDING_TOOL]
            )
        )
    )
    source_urls = extract_source_urls(response)
    grounding_hit = len(source_urls) > 0

    return response.text, source_urls, grounding_hit

async def fetch_competitor_data(competitor_name: str,category: str) -> tuple[dict,dict,list[str],bool]:
    product_prompt = build_product_details_prompt(competitor_name)
    trends_prompt = build_trends_prompt(competitor_name,category)

    (product_text, product_sources, product_grounding_hit), \
    (trends_text, trends_sources, trends_grounding_hit) = await asyncio.gather(
        call_gemini_with_grounding(product_prompt),
        call_gemini_with_grounding(trends_prompt)
    )

    product_data = json.loads(clean_json_response(product_text))
    trends_data = json.loads(clean_json_response(trends_text))

    all_source_urls = list(set(product_sources + trends_sources))
    grounding_hit = product_grounding_hit or trends_grounding_hit

    return product_data, trends_data, all_source_urls, grounding_hit

async def research_competitor(
    competitor_name: str,
    category: str,
    max_retries: int = 2
) -> ToolResult:
    last_error = None
    fallback_used = False

    for attempt in range(max_retries + 1):
        try:
            product_data, trends_data, source_urls, grounding_hit = \
                await fetch_competitor_data(competitor_name, category)

            merged = {
                **product_data,
                **trends_data,
                "source_urls": source_urls
            }

            result = CompetitorResult(**merged)

            log_tool_call(
                competitor_name = competitor_name,
                grounding_hit = grounding_hit,
                fallback_used = fallback_used
            )

            return ToolResult(success = True, data = result, fallback_used = fallback_used)
        
        except(ValidationError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(
                f"Attempt {attempt + 1} is failed | "
                f"Competitor Name = {competitor_name} | "
                f"Error = {last_error}"
            )
            fallback_used = True

            if attempt == max_retries:
                log_tool_call(
                    competitor_name = competitor_name,
                    grounding_hit = False,
                    fallback_used = fallback_used
                )

                return ToolResult(
                    success = False,
                    fallback_used = True,
                    error = f"Maximum Attempt has reached: {last_error}"
                )

    return ToolResult(success = False, fallback_used = True, error = "Unexpected Error")

async def run_competitor_research_tool(
    competitor_names: list[str],
    category: str
) -> list[ToolResult]:
    logger.info(f"{len(competitor_names)} rival searching | Category = {category}")

    results = await asyncio.gather(
        *[research_competitor(name, category) for name in competitor_names],
        return_exceptions = True
    )

    tool_results = []
    for name, result in zip(competitor_names, results):
        if isinstance(result, Exception):
            logger.error(f"Unexpected error | competitor_name = {name} | error = {result}")
            tool_results.append(ToolResult(
                success = False,
                fallback_used = True,
                error = str(result)
            ))
        else:
            tool_results.append(result)

    return tool_results