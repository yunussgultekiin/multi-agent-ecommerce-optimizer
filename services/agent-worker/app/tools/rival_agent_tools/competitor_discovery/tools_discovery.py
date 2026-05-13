import asyncio
import json
import logging
from pydantic import ValidationError
from google import genai
from google.genai import types
from .models_discovery import DiscoveryResult, DiscoveryToolResult
from .prompts_discovery import build_discovery_prompt
from .utils_discovery import extract_source_urls, clean_json_response, log_tool_call

logger = logging.getLogger(__name__)
_client = genai.Client()
_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())

async def run_competitor_discovery_tool(
    platform: str,
    category: str,
    product_title: str,
    brand: str,
    max_retries: int = 2,
) -> DiscoveryToolResult:
    prompt = build_discovery_prompt(platform, category, product_title, brand)
    last_error = None
    fallback_used = False
    loop = asyncio.get_running_loop()

    for attempt in range(max_retries + 1):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: _client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=[_GROUNDING_TOOL]),
                ),
            )
            source_urls = extract_source_urls(response)
            grounding_hit = len(source_urls) > 0
            cleaned = clean_json_response(response.text)
            data = json.loads(cleaned)
            result = DiscoveryResult(source_urls=source_urls, **data)

            log_tool_call(
                platform=platform,
                category=category,
                discovered_count=len(result.competitors),
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
            )
            return DiscoveryToolResult(success=True, data=result, fallback_used=fallback_used)

        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning("Discovery attempt %d failed | platform=%s error=%s", attempt + 1, platform, last_error)
            fallback_used = True

            if attempt == max_retries:
                log_tool_call(platform=platform, category=category, discovered_count=0, grounding_hit=False, fallback_used=True)
                return DiscoveryToolResult(success=False, fallback_used=True, error=f"Max retries reached: {last_error}")

    return DiscoveryToolResult(success=False, fallback_used=True, error="Unexpected error")
