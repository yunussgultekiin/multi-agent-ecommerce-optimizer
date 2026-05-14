import asyncio
import json
import logging
from pydantic import ValidationError
from google import genai
from .models_market import MarketGapResult, ToolResult
from .prompts_market import build_market_gap_prompt, build_self_correction_prompt
from .utils_market import filter_valid_competitors, normalize_user_product, clean_json_response, log_tool_call

logger = logging.getLogger(__name__)

client = genai.Client()

async def call_gemini(prompt: str) -> str:
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model = "gemini-2.0-flash",
            contents = prompt
        )
    )

    return response.text or ""

async def analyze_market_gap(
    user_product: dict,
    competitors: list[dict],
    max_retries: int = 2
) -> ToolResult:
    normalized_user_product = normalize_user_product(user_product)
    prompt = build_market_gap_prompt(normalized_user_product,competitors)
    last_error = None

    for attempt in range(max_retries + 1):
        current_prompt = (
            build_self_correction_prompt(prompt, last_error)
            if attempt > 0
            else prompt
        )

        try:
            response_text = await call_gemini(current_prompt)
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            result = MarketGapResult(**data)

            log_tool_call(
                valid_competitor_count = len(competitors),
                fallback_used = False,
                positioning_score = result.positioning_score
            )

            return ToolResult(success = True, data = result, fallback_used = False)

        except (ValidationError, json.JSONDecodeError) as e:
            last_error = str(e)
            logger.warning(
                f"Attempt {attempt + 1} is failed | "
                f"Error = {last_error}"
            )

            if attempt == max_retries:
                log_tool_call(
                    valid_competitor_count = len(competitors),
                    fallback_used = True,
                    positioning_score = None
                )

                return ToolResult(
                    success = False,
                    fallback_used = True,
                    error = f"Maximum attempt reached : {last_error}"
                )
        
    return ToolResult(success = False, fallback_used = True, error = "Unexpected Error")

async def run_market_gap_analyzer(
    user_product: dict,
    competitor_tool_results: list[ToolResult]
) -> ToolResult:
    valid_competitors = filter_valid_competitors(competitor_tool_results)

    if not valid_competitors:
        logger.warning("Not enough valid competitors found, performing fallback analysis.")

        log_tool_call(
            valid_competitor_count = 0,
            fallback_used = True,
            positioning_score = None
        )

        return ToolResult(
            success = False,
            fallback_used = True,
            error = "Not enough valid competitors found"
        )

    logger.info(f"Analyzing {len(valid_competitors)} valid competitors")

    return await analyze_market_gap(user_product, valid_competitors)
