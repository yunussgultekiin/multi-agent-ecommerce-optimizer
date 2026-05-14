import logging
from typing import Optional
from .models_market import ToolResult

logger = logging.getLogger(__name__)

def filter_valid_competitors(tool_results: list[ToolResult]) -> list[dict]:
    valid = []
    for result in tool_results:
        if result.success and result.data is not None:
            competitor = result.data
            valid.append({
                "competitor_name": competitor.competitor_name,
                "brand": competitor.brand,
                "price": competitor.price,
                "features": competitor.features,
                "rating": competitor.rating,
                "review_count": competitor.review_count,
                "variants": competitor.variants,
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
    text = raw_text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.lower().startswith("json"):
            text = text[4:]
    
    return text.strip()

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