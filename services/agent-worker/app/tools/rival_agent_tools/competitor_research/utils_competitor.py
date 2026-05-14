import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

def clean_json_response(raw_text: str) -> str:
    text = (raw_text or "").strip()

    fenced_json = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if fenced_json:
        return fenced_json.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1].strip()

    return text

def parse_json_response(raw_text: str) -> dict:
    cleaned = clean_json_response(raw_text)
    parsed = json.loads(cleaned)

    if not isinstance(parsed, dict):
        raise ValueError("Gemini response must be a JSON object")

    return parsed

def _add_url(urls: list[str], value: Any) -> None:
    if not isinstance(value, str): return
    url = value.strip()
    if not url.startswith(("http://", "https://")): return
    urls.append(url)

def extract_source_urls(response: Any) -> list[str]:
    urls: list[str] = []

    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        if not grounding_metadata: continue

        grounding_chunks = getattr(grounding_metadata, "grounding_chunks", None) or []

        for chunk in grounding_chunks:
            web = getattr(chunk, "web", None)
            if web: _add_url(urls, getattr(web, "uri", None))

        grounding_supports = getattr(grounding_metadata, "grounding_supports", None) or []

        for support in grounding_supports:
            segment = getattr(support, "segment", None)
            if segment: _add_url(urls, getattr(segment, "uri", None))

    return list(dict.fromkeys(urls))

def log_tool_call(
    competitor_name: str,
    platform: str,
    grounding_hit: bool,
    fallback_used: bool,
    visual_ready: bool,
) -> None:
    logger.info(
        "CompetitorResearchTool call",
        extra={
            "competitor_name": competitor_name,
            "platform": platform,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
            "visual_ready": visual_ready,
        },
    )

def log_research_summary(
    input_count: int,
    processed_count: int,
    successful_count: int,
    visual_ready_count: int,
    fallback_used: bool,
) -> None:
    logger.info(
        "CompetitorResearchTool summary",
        extra={
            "input_count": input_count,
            "processed_count": processed_count,
            "successful_count": successful_count,
            "visual_ready_count": visual_ready_count,
            "fallback_used": fallback_used,
        },
    )