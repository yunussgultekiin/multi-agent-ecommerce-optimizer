import json
import logging
import re

logger = logging.getLogger(__name__)

def extract_competitor_names(competitor_names: list[dict]) -> list[str]:
    names = []
    for c in competitor_names or []:
        name = c.get("competitor_name", "").strip()
        if name:
            names.append(name)
    return names

def extract_research_context(competitor_research_results: list[dict]) -> list[dict]:
    context = []
    for r in competitor_research_results or []:
        if not r.get("success") or not r.get("data"):
            continue
        data = r["data"]
        entry: dict = {}
        if data.get("competitor_name"):
            entry["competitor_name"] = data["competitor_name"]
        if data.get("features"):
            entry["features"] = data["features"]
        if data.get("rating") is not None:
            entry["rating"] = data["rating"]
        if data.get("review_count") is not None:
            entry["review_count"] = data["review_count"]
        if data.get("category_trends"):
            entry["category_trends"] = data["category_trends"]
        if entry:
            context.append(entry)
    return context

def _sanitize_control_chars(text: str) -> str:
    result: list[str] = []
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\":
                result.append(ch)
                i += 1
                if i < len(text):
                    result.append(text[i])
                i += 1
                continue
            elif ch == '"':
                in_string = False
                result.append(ch)
            elif ord(ch) < 0x20:
                if ch == "\n":
                    result.append("\\n")
                elif ch == "\r":
                    result.append("\\r")
                elif ch == "\t":
                    result.append("\\t")
                else:
                    result.append(f"\\u{ord(ch):04x}")
            else:
                result.append(ch)
        else:
            if ch == '"':
                in_string = True
            result.append(ch)
        i += 1
    return "".join(result)

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

    text = _sanitize_control_chars(text)
    text = re.sub(r",\s*([\]}])", r"\1", text)

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response must be a JSON object")
    return parsed

def log_tool_call(
    competitor_count: int,
    pain_point_count: int,
    praised_feature_count: int,
    grounding_hit: bool,
    fallback_used: bool,
) -> None:
    logger.info(
        "SentimentAnalyzerTool call completed",
        extra={
            "competitor_count": competitor_count,
            "pain_point_count": pain_point_count,
            "praised_feature_count": praised_feature_count,
            "grounding_hit": grounding_hit,
            "fallback_used": fallback_used,
        },
    )
