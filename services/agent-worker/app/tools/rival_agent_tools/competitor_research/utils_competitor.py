import json
import logging
import re

logger = logging.getLogger(__name__)


def parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            text = text[first : last + 1].strip()

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response must be a JSON object")
    return parsed


def log_tool_call(
    competitor_name: str,
    platform: str,
    estimated_price: float | None,
    feature_count: int,
    grounding_hit: bool,
    fallback_used: bool,
) -> None:
    logger.info(
        "CompetitorResearchTool call completed",
        extra={
            "competitor_name": competitor_name,
            "platform": platform,
            "estimated_price": estimated_price,
            "feature_count": feature_count,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
        },
    )


def log_research_summary(
    input_count: int,
    processed_count: int,
    successful_count: int,
    fallback_used: bool,
) -> None:
    logger.info(
        "CompetitorResearchTool summary",
        extra={
            "input_count": input_count,
            "processed_count": processed_count,
            "successful_count": successful_count,
            "fallback_used": fallback_used,
        },
    )
