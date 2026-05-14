import json
import logging
import re
from typing import Any
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

_KNOWN_CDN_DOMAINS: dict[str, list[str]] = {
    "trendyol": ["cdn.dsmcdn.com"],
    "hepsiburada": ["productimages.hepsiburada.net", "images.hepsiburada.net"],
    "amazon": ["m.media-amazon.com", "images-na.ssl-images-amazon.com"],
}

_CDN_IMAGE_PATTERNS = [
    "cdn.dsmcdn.com",
    "productimages.hepsiburada.net",
    "images.hepsiburada.net",
    "m.media-amazon.com",
    "images-na.ssl-images-amazon.com",
]

_REJECT_IMAGE_PATTERNS = [
    "placeholder",
    "product-.22",
    "data:image",
    "base64,",
    "logo",
    "/icon",
    "/favicon",
    ".svg",
    "1x1",
    "blank.",
    "spacer.",
    "transparent.",
]

MAX_IMAGE_URLS = 5


def validate_image_url(url: str, platform: str = "") -> bool:
    if not isinstance(url, str):
        return False

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        return False

    if url.startswith("data:"):
        return False

    lower_url = url.lower()

    for pat in _REJECT_IMAGE_PATTERNS:
        if pat in lower_url:
            return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    netloc = parsed.netloc.lower()
    path = parsed.path.lower()

    cdn_domains = _KNOWN_CDN_DOMAINS.get(platform, [])

    if cdn_domains and any(cdn in netloc for cdn in cdn_domains):
        return True

    if any(cdn in netloc for cdn in _CDN_IMAGE_PATTERNS):
        return True

    if re.search(r"\.(jpe?g|png|webp|gif|avif)(\?|$)", path):
        return True

    return False


def extract_cdn_images_from_sources(source_urls: list[str], platform: str = "") -> list[str]:
    """Filter grounding source URLs for direct CDN product image URLs when grounding exposes them."""
    found: list[str] = []
    seen: set[str] = set()

    for raw_url in source_urls or []:
        if not isinstance(raw_url, str):
            continue

        candidates = [
            raw_url.strip(),
            unquote(raw_url.strip()),
        ]

        for url in candidates:
            if not url or url in seen:
                continue

            lower_url = url.lower()

            if not any(cdn in lower_url for cdn in _CDN_IMAGE_PATTERNS):
                continue

            if not validate_image_url(url, platform):
                continue

            found.append(url)
            seen.add(url)

            if len(found) >= MAX_IMAGE_URLS:
                return found

    return found


def filter_image_urls(urls: list[str], platform: str = "") -> list[str]:
    valid: list[str] = []
    seen: set[str] = set()

    for url in urls or []:
        if not isinstance(url, str):
            continue

        url = url.strip()

        if url in seen:
            continue

        if validate_image_url(url, platform):
            valid.append(url)
            seen.add(url)

        if len(valid) >= MAX_IMAGE_URLS:
            break

    return valid


def merge_image_urls(
    source_image_urls: list[str],
    gemini_image_urls: list[str],
    platform: str = "",
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for url in [*(source_image_urls or []), *(gemini_image_urls or [])]:
        if not isinstance(url, str):
            continue

        url = url.strip()

        if not url or url in seen:
            continue

        if not validate_image_url(url, platform):
            continue

        merged.append(url)
        seen.add(url)

        if len(merged) >= MAX_IMAGE_URLS:
            break

    return merged


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
    if not isinstance(value, str):
        return

    url = value.strip()

    if url.startswith(("http://", "https://")):
        urls.append(url)


def extract_source_urls(response: Any) -> list[str]:
    urls: list[str] = []

    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)

        if not grounding_metadata:
            continue

        grounding_chunks = getattr(grounding_metadata, "grounding_chunks", None) or []

        for chunk in grounding_chunks:
            web = getattr(chunk, "web", None)

            if web:
                _add_url(urls, getattr(web, "uri", None))

        grounding_supports = getattr(grounding_metadata, "grounding_supports", None) or []

        for support in grounding_supports:
            segment = getattr(support, "segment", None)

            if segment:
                _add_url(urls, getattr(segment, "uri", None))

    return list(dict.fromkeys(urls))


def log_tool_call(
    competitor_name: str,
    platform: str,
    grounding_hit: bool,
    fallback_used: bool,
    visual_ready: bool,
    gemini_image_count: int = 0,
    source_image_count: int = 0,
    final_image_count: int = 0,
    image_source: str = "none",
) -> None:
    logger.info(
        "CompetitorResearchTool call",
        extra={
            "competitor_name": competitor_name,
            "platform": platform,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
            "visual_ready": visual_ready,
            "gemini_image_count": gemini_image_count,
            "source_image_count": source_image_count,
            "final_image_count": final_image_count,
            "image_source": image_source,
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