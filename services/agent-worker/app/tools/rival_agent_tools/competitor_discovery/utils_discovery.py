import asyncio
import json
import logging
import re
from typing import Any
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_PLATFORM_DOMAINS = {
    "trendyol": "trendyol.com",
    "amazon": "amazon.com.tr",
    "hepsiburada": "hepsiburada.com",
}

_FAKE_URL_PATTERNS = [
    "p-123456789",
    "p-112233445",
    "p-192837462",
    "placeholder",
    "example.com",
    "/test-",
    "-test-p-",
]

_REJECT_PATH_SEGMENTS = {
    "/search", "/cart", "/sepet", "/kampanya",
    "/liste", "/category", "/kategori", "/favorites",
    "/wishlist", "/checkout", "/hesabim", "/magaza",
    "/sr", "/butik", "/marka",
}

_TRENDYOL_PRODUCT_ID_RE = re.compile(r"[/-]p-(\d{6,})(?:[/?#]|$)")


def extract_trendyol_product_id(url: str) -> str | None:
    match = _TRENDYOL_PRODUCT_ID_RE.search(url or "")
    return match.group(1) if match else None


def normalize_url_for_compare(url: str) -> str:
    parsed = urlparse((url or "").strip())
    path = parsed.path.rstrip("/")

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",
        "",
        "",
    ))


def is_probably_valid_product_url(url: str, platform: str) -> bool:
    if not isinstance(url, str):
        return False

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    if not parsed.netloc:
        return False

    domain = _PLATFORM_DOMAINS.get(platform, "")

    if domain and domain not in parsed.netloc.lower():
        return False

    lower_url = url.lower()

    for pat in _FAKE_URL_PATTERNS:
        if pat in lower_url:
            return False

    path = parsed.path.lower()

    for seg in _REJECT_PATH_SEGMENTS:
        if path.startswith(seg) or f"{seg}/" in path:
            return False

    if platform == "trendyol":
        if "-p-" not in path and "/p-" not in path:
            return False

        if not extract_trendyol_product_id(url):
            return False

    return True


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
    if not isinstance(value, str):
        return

    url = value.strip()

    if url.startswith(("http://", "https://")):
        urls.append(url)


def extract_source_urls(response: Any) -> list[str]:
    source_urls: list[str] = []

    try:
        candidates = getattr(response, "candidates", None) or []

        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            if not metadata:
                continue

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


def _resolve_redirect_sync(url: str, timeout: int = 6) -> str | None:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 compatible; GoogleHackathonBot/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    for method in ("HEAD", "GET"):
        try:
            request = Request(url, headers=headers, method=method)

            with urlopen(request, timeout=timeout) as response:
                return response.geturl()

        except Exception:
            continue

    return None


async def resolve_grounding_source_urls(source_urls: list[str]) -> list[str]:
    loop = asyncio.get_running_loop()

    valid_sources = [
        url for url in source_urls or []
        if isinstance(url, str) and url.startswith(("http://", "https://"))
    ]

    if not valid_sources:
        return []

    tasks = [
        loop.run_in_executor(None, _resolve_redirect_sync, url)
        for url in valid_sources
    ]

    resolved = await asyncio.gather(*tasks, return_exceptions=True)

    urls: list[str] = []

    for original, value in zip(valid_sources, resolved):
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            urls.append(value)
        else:
            urls.append(original)

    return list(dict.fromkeys(urls))


def build_grounded_product_url_candidates(
    source_urls: list[str],
    resolved_source_urls: list[str],
    platform: str,
) -> list[tuple[int, str]]:
    """
    Returns product URL candidates from grounding metadata only.

    tuple:
      (source_url_index, final_product_url)

    source_url_index is based on original source_urls order.
    """
    candidates: list[tuple[int, str]] = []
    seen: set[str] = set()

    for idx, original_url in enumerate(source_urls or []):
        possible_urls: list[str] = []

        if idx < len(resolved_source_urls):
            possible_urls.append(resolved_source_urls[idx])

        possible_urls.append(original_url)

        for url in possible_urls:
            if not is_probably_valid_product_url(url, platform):
                continue

            normalized = normalize_url_for_compare(url)

            if normalized in seen:
                continue

            seen.add(normalized)
            candidates.append((idx, url))
            break

    return candidates


def choose_grounded_url_for_candidate(
    source_url_index: int | None,
    product_url_candidates: list[tuple[int, str]],
    used_normalized_urls: set[str],
) -> tuple[int | None, str | None, bool]:
    """
    Returns:
      source_url_index, product_url, used_requested_index
    """
    if source_url_index is not None:
        for idx, url in product_url_candidates:
            normalized = normalize_url_for_compare(url)

            if idx == source_url_index and normalized not in used_normalized_urls:
                return idx, url, True

    for idx, url in product_url_candidates:
        normalized = normalize_url_for_compare(url)

        if normalized not in used_normalized_urls:
            return idx, url, False

    return None, None, False


def log_tool_call(
    platform: str,
    category: str,
    discovered_count: int,
    grounding_hit: bool,
    fallback_used: bool,
    valid_url_count: int = 0,
    rejected_url_count: int = 0,
    duplicate_pid_count: int = 0,
    rejected_ungrounded_url_count: int = 0,
    source_url_count: int = 0,
    resolved_source_url_count: int = 0,
    source_index_used_count: int = 0,
    fallback_source_pick_count: int = 0,
) -> None:
    logger.info(
        "CompetitorDiscoveryTool completed",
        extra={
            "platform": platform,
            "category": category,
            "discovered_count": discovered_count,
            "valid_url_count": valid_url_count,
            "rejected_url_count": rejected_url_count,
            "duplicate_pid_count": duplicate_pid_count,
            "rejected_ungrounded_url_count": rejected_ungrounded_url_count,
            "source_url_count": source_url_count,
            "resolved_source_url_count": resolved_source_url_count,
            "source_index_used_count": source_index_used_count,
            "fallback_source_pick_count": fallback_source_pick_count,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
        },
    )