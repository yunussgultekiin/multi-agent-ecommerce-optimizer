import logging
import re
from typing import Optional
from app.core import ToolResult

logger = logging.getLogger(__name__)

def filter_valid_competitors(tool_results: list[ToolResult]) -> list[dict]:
    valid = []
    for result in tool_results:
        if result.success and result.data:
            d = result.data
            valid.append({
                "competitor_name": d.get("competitor_name"),
                "brand": d.get("brand"),
                "price": d.get("price"),
                "features": d.get("features", []),
                "rating": d.get("rating"),
                "review_count": d.get("review_count"),
                "variants": d.get("variants", []),
            })

    return valid

def normalize_user_product(user_product: dict) -> dict:
    return {
        "title": user_product.get("title", ""),
        "brand": user_product.get("brand", ""),
        "price": user_product.get("price", None),
        "category": user_product.get("category", ""),
        "features": user_product.get("features", []),
        "variants": user_product.get("variants", []),
    }

def clean_json_response(raw_text: str) -> str:
    text = (raw_text or "").strip()

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1].strip()

    return text

def log_tool_call(
    valid_competitor_count: int,
    fallback_used: bool,
    positioning_score: Optional[float]
) -> None:
    logger.info(
        "MarketGapAnalyzer call completed | "
        f"valid_competitor_count={valid_competitor_count} | "
        f"fallback_used={fallback_used} | "
        f"positioning_score={positioning_score}"
    )