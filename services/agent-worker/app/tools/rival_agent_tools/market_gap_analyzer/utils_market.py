import logging
import re
from typing import Optional
from app.core import ToolResult

logger = logging.getLogger(__name__)

def filter_valid_competitors(tool_results: list[ToolResult]) -> list[dict]:
    valid = []
    for result in tool_results:
        if result.success and result.data:
            data = result.data
            valid.append({
                "competitor_name": data.get("competitor_name"),
                "brand": data.get("brand"),
                "estimated_price": data.get("estimated_price"),
                "features": data.get("features", []),
                "rating": data.get("rating"),
                "review_count": data.get("review_count"),
                "variants": data.get("variants", []),
                "trending_keywords": data.get("trending_keywords", []),
                "category_trends": data.get("category_trends"),
            })
    return valid


def normalize_user_product(user_product: dict) -> dict:
    return {
        "title": user_product.get("title", ""),
        "brand": user_product.get("brand", ""),
        "price": user_product.get("price"),
        "category": user_product.get("category", ""),
        "description": user_product.get("description", ""),
        "seo_keywords": user_product.get("seo_keywords", []),
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
    pain_point_count: int,
    trend_count: int,
    fallback_used: bool,
    positioning_score: Optional[float],
) -> None:
    logger.info(
        "MarketGapAnalyzer call completed",
        extra={
            "valid_competitor_count": valid_competitor_count,
            "pain_point_count": pain_point_count,
            "trend_count": trend_count,
            "fallback_used": fallback_used,
            "positioning_score": positioning_score,
        },
    )