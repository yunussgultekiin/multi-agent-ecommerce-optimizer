import logging
import re

logger = logging.getLogger(__name__)

def extract_source_urls(response) -> list[str]:
    source_urls = []
    try:
        metadata = response.candidates[0].grounding_metadata
        if metadata and metadata.grounding_chunks:
            for chunk in metadata.grounding_chunks:
                if chunk.web and chunk.web.uri:
                    source_urls.append(chunk.web.uri)
    except (AttributeError, IndexError):
        pass
    return source_urls

def clean_json_response(raw_text: str) -> str:
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text

def log_tool_call(platform: str, category: str, discovered_count: int, grounding_hit: bool, fallback_used: bool) -> None:
    logger.info(
        "CompetitorDiscoveryTool completed | platform=%s category=%s discovered_count=%d grounding_hit=%s fallback_used=%s",
        platform, category, discovered_count, grounding_hit, fallback_used,
    )
