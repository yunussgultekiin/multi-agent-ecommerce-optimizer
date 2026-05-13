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

def log_tool_call(
    competitor_name: str,
    grounding_hit: bool,
    fallback_used: bool
) -> None:
    logger.info(
        "CompetitorResearchTool call completed | "
        f"Competitor Name: {competitor_name} | "
        f"Ground Hit: {grounding_hit} | "
        f"Fallback: {fallback_used}"
    )