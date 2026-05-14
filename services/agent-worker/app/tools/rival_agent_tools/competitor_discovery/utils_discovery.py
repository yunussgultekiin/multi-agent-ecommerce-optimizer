import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

def clean_json_response(raw_text: str) -> str:
    text = (raw_text or "").strip()

    fenced_json = re.search(
        r"```(?:json)?\s*([\s\S]*?)```",
        text,
        re.IGNORECASE,
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
        raise ValueError("Discovery response must be a JSON object")

    return parsed

def _add_url(urls: list[str], value: Any) -> None:
    if not isinstance(value, str): return
    url = value.strip()
    
    if url.startswith(("http://", "https://")):
        urls.append(url)

def extract_source_urls(response: Any) -> list[str]:
    source_urls: list[str] = []

    try:
        candidates = getattr(response, "candidates", None) or []

        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata: continue

            grounding_chunks = getattr(metadata, "grounding_chunks", None) or []

            for chunk in grounding_chunks:
                web = getattr(chunk, "web", None)

                if web:
                    _add_url(source_urls, getattr(web, "uri", None))

            grounding_supports = getattr(metadata, "grounding_supports", None) or []

            for support in grounding_supports:
                segment = getattr(support, "segment", None)

                if segment:
                    _add_url(source_urls, getattr(segment, "uri", None))

    except Exception:
        logger.exception("Failed to extract grounding source URLs")

    return list(dict.fromkeys(source_urls))

def log_tool_call(
    platform: str,
    category: str,
    discovered_count: int,
    grounding_hit: bool,
    fallback_used: bool,
) -> None:
    logger.info(
        "CompetitorDiscoveryTool completed",
        extra={
            "platform": platform,
            "category": category,
            "discovered_count": discovered_count,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
        },
    )