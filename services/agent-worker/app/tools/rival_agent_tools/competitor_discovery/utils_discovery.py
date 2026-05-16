import json
import logging
import re

logger = logging.getLogger(__name__)

def parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty response")

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            text = text[first : last + 1].strip()

    text = re.sub(r":\s*NaN\b", ": null", text)
    text = re.sub(r":\s*Infinity\b", ": null", text)
    text = re.sub(r":\s*-Infinity\b", ": null", text)

    if not text:
        raise ValueError("No JSON object found in Gemini response")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.debug("JSON parse failed | snippet=%r", text[:300])
        raise ValueError(f"Invalid JSON from Gemini: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Gemini response must be a JSON object, got {type(parsed).__name__}")

    return parsed

def log_tool_call(
    platform: str,
    category: str,
    discovered_count: int,
    grounding_hit: bool,
    fallback_used: bool,
) -> None:
    logger.info(
        "CompetitorDiscoveryTool call completed",
        extra={
            "platform": platform,
            "category": category,
            "discovered_count": discovered_count,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
        },
    )