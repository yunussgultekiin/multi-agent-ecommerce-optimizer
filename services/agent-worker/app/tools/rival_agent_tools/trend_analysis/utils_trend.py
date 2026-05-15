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
    category: str,
    platform: str,
    trend_count: int,
    grounding_hit: bool,
    fallback_used: bool,
) -> None:
    logger.info(
        "TrendAnalyzerTool call completed",
        extra={
            "category": category,
            "platform": platform,
            "trend_count": trend_count,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
        },
    )
