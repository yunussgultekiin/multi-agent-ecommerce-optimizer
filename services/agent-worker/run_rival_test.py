"""
Rival Agent end-to-end test.

Prerequisites:
  gcloud auth application-default login --no-launch-browser
  export GOOGLE_CLOUD_PROJECT=<your-project-id>

Usage:
  cd services/agent-worker
  python run_rival_test.py
"""

import asyncio
from datetime import datetime
from dotenv import load_dotenv
import json
import os
from pathlib import Path
import sys
import time

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

os.environ.setdefault("JWT_SECRET_KEY", "local-test-key")

print("── Env ──────────────────────────────────────────────────")
for _k in (
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GEMINI_FLASH_MODEL",
    "GEMINI_PRO_MODEL",
):
    print(f"  {_k}={os.environ.get(_k, '(not set)')}")
print("─────────────────────────────────────────────────────────")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TASK_SERVICE_URL", "http://localhost:8080")

sys.path.insert(0, str(Path(__file__).parent))

from app.core import ToolResult
from app.tools.rival_agent_tools import (
    run_competitor_discovery_tool,
    run_competitor_research_tool,
    run_market_gap_analyzer,
    run_sentiment_analyzer,
    run_smart_pricing_engine,
    run_trend_analyzer,
)

USER_PRODUCT = {
    "title": "60 Parça 12 Kişilik Çelik Düz Çatal Kaşık Seti Takımı",
    "brand": "Zagori",
    "category": "mutfak",
    "price": 600.00,
    "description": "12 kişilik geniş kapasiteye sahip, her türlü sofranız için ideal bir seçim olan Zagori çatal-kaşık seti, aile yemeklerinden özel davetlere kadar her ortamda şıklığı ve kullanışlılığı bir arada sunar",
    "features": [
        "Mutfak",
        "Kaşık",
        "Çatal",
        "Mutfak Seti",
    ],
    "variants": [
        {
            "name": "12 Kişilik Çelik Düz Çatal Kaşık Seti",
            "price": 600.00,
            "price_delta": 50.0,
        },
    ],
    "rating": None,
    "review_count": None,
}

TARGET_PLATFORM = "trendyol"


def _save(output_dir: Path, filename: str, data: object) -> None:
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  saved → {path.name}")


def _tool_result_to_dict(result: ToolResult) -> dict:
    return {
        "success": result.success,
        "fallback_used": result.fallback_used,
        "data": result.data,
    }


async def main() -> None:
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(__file__).parent / "test_outputs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"Rival Agent Test  |  {run_id}")
    print(f"Output dir: {output_dir}")
    print(f"{'=' * 60}\n")

    timing: dict[str, float] = {}
    flow_start = time.perf_counter()

    print("[1/6] CompetitorDiscoveryTool")
    t0 = time.perf_counter()
    discovery_result = await run_competitor_discovery_tool(
        platform=TARGET_PLATFORM,
        category=USER_PRODUCT["category"],
        product_title=USER_PRODUCT["title"],
        brand=USER_PRODUCT["brand"],
    )
    timing["discovery"] = round(time.perf_counter() - t0, 2)
    print(
        f"  success={discovery_result.success}  fallback={discovery_result.fallback_used}  elapsed={timing['discovery']}s"
    )
    _save(output_dir, "01_discovery.json", _tool_result_to_dict(discovery_result))

    competitor_names: list[dict] = []
    if discovery_result.success and discovery_result.data:
        competitor_names = discovery_result.data.get("competitors", [])
        print(f"  found {len(competitor_names)} competitors")
    else:
        print("  WARNING: discovery failed — downstream tools will use empty list")

    print("\n[2/6] CompetitorResearchTool")
    t0 = time.perf_counter()
    research_results = await run_competitor_research_tool(
        competitors=competitor_names,
        category=USER_PRODUCT["category"],
    )
    timing["research"] = round(time.perf_counter() - t0, 2)
    successful = sum(1 for r in research_results if r.success)
    print(
        f"  success={successful}/{len(research_results)}  elapsed={timing['research']}s"
    )
    _save(
        output_dir,
        "02_research.json",
        [_tool_result_to_dict(r) for r in research_results],
    )

    research_dicts = [
        {"success": r.success, "data": r.data, "fallback_used": r.fallback_used}
        for r in research_results
    ]

    def _to_tool_results(dicts: list[dict]) -> list[ToolResult]:
        return [
            ToolResult(
                success=d.get("success", False),
                data=d.get("data") or {},
                fallback_used=d.get("fallback_used", False),
            )
            for d in dicts
        ]

    print("\n[3+4/6] SentimentAnalyzerTool + TrendAnalyzerTool  (parallel)")
    t0 = time.perf_counter()
    sentiment_result_obj, trend_result_obj = await asyncio.gather(
        run_sentiment_analyzer(
            competitor_names=competitor_names,
            competitor_research_results=research_dicts,
            category=USER_PRODUCT["category"],
            target_platform=TARGET_PLATFORM,
            user_product=USER_PRODUCT,
        ),
        run_trend_analyzer(
            category=USER_PRODUCT["category"],
            target_platform=TARGET_PLATFORM,
            user_product=USER_PRODUCT,
        ),
    )
    timing["sentiment_and_trend_parallel"] = round(time.perf_counter() - t0, 2)
    print(
        f"  sentiment: success={sentiment_result_obj.success}  fallback={sentiment_result_obj.fallback_used}"
    )
    print(
        f"  trend:     success={trend_result_obj.success}  fallback={trend_result_obj.fallback_used}"
    )
    print(
        f"  elapsed={timing['sentiment_and_trend_parallel']}s  (both ran concurrently)"
    )
    _save(output_dir, "03_sentiment.json", _tool_result_to_dict(sentiment_result_obj))
    _save(output_dir, "04_trend.json", _tool_result_to_dict(trend_result_obj))

    sentiment_data = sentiment_result_obj.data if sentiment_result_obj.success else {}
    trend_data = trend_result_obj.data if trend_result_obj.success else {}

    print("\n[5/6] MarketGapAnalyzer")
    t0 = time.perf_counter()
    gap_result = await run_market_gap_analyzer(
        user_product=USER_PRODUCT,
        competitor_tool_results=_to_tool_results(research_dicts),
        sentiment_result=sentiment_data,
        trend_result=trend_data,
    )
    timing["market_gap"] = round(time.perf_counter() - t0, 2)
    print(
        f"  success={gap_result.success}  fallback={gap_result.fallback_used}  elapsed={timing['market_gap']}s"
    )
    _save(output_dir, "05_market_gap.json", _tool_result_to_dict(gap_result))

    print("\n[6/6] SmartPricingEngine")
    t0 = time.perf_counter()
    pricing_result = await run_smart_pricing_engine(
        user_product=USER_PRODUCT,
        competitor_tool_results=_to_tool_results(research_dicts),
        gap_result=gap_result.data if gap_result.success else None,
        sentiment_result=sentiment_data,
        trend_result=trend_data,
        target_platform=TARGET_PLATFORM,
    )
    timing["pricing"] = round(time.perf_counter() - t0, 2)
    print(
        f"  success={pricing_result.success}  fallback={pricing_result.fallback_used}  elapsed={timing['pricing']}s"
    )
    _save(output_dir, "06_pricing.json", _tool_result_to_dict(pricing_result))

    timing["total_flow"] = round(time.perf_counter() - flow_start, 2)

    rival_json = {
        "user_product": USER_PRODUCT,
        "target_platform": TARGET_PLATFORM,
        "competitors": competitor_names,
        "competitor_research_results": research_dicts,
        "sentiment_result": sentiment_data,
        "trend_result": trend_data,
        "gap_result": gap_result.data if gap_result.success else {},
        "pricing_result": pricing_result.data if pricing_result.success else {},
    }

    print("\n[Final] Saving rival_json and timing report")
    _save(output_dir, "final_rival_json.json", rival_json)
    _save(output_dir, "timing_report.json", timing)

    print(f"\n{'=' * 60}")
    print("Timing Summary")
    print(f"{'=' * 60}")
    for step, elapsed in timing.items():
        label = f"  {step:<30}"
        print(f"{label} {elapsed:>6.2f}s")
    print(f"{'=' * 60}")
    print(f"  {'TOTAL':<30} {timing['total_flow']:>6.2f}s")
    print(f"{'=' * 60}\n")
    print(f"All outputs saved to: {output_dir}\n")


if __name__ == "__main__":
    asyncio.run(main())
