import argparse
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import json
import logging
import os
from pathlib import Path
import sys
import time

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

os.environ.setdefault("JWT_SECRET_KEY", "local-test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TASK_SERVICE_URL", "http://localhost:8080")

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s — %(message)s",
)

from app.chroma_client import seed_seo_chunks
from app.config import settings
from app.core import ToolResult
from app.tools.rival_agent_tools import (
    run_competitor_discovery_tool,
    run_competitor_research_tool,
    run_market_gap_analyzer,
    run_sentiment_analyzer,
    run_smart_pricing_engine,
    run_trend_analyzer,
)
from app.tools.seo_agent_tools.image_generation.prompts_image import build_image_prompt
from app.tools.seo_agent_tools.image_generation.utils_image import select_variant
from app.tools.seo_agent_tools.seo_optimizer.tools_seo import SeoOptimizerTool
from app.tools.seo_agent_tools.seo_optimizer.models_seo import SeoOptimizerInput

LOCAL_IMAGE_PATH: Path | None = Path(__file__).parent / "test_picture.png"

USER_PRODUCT: dict = {
    "title": "Ahşap Kollu Çizgili Katlanır Kamp Sandalyesi",
    "brand": "CampRoute",
    "category": "Kamp & Outdoor",
    "price": 549.90,
    "description": (
        "Kampta, plajda veya piknikte rahatça kullanabileceğiniz katlanabilir sandalye. "
        "Kolları gerçek ahşaptır, plastik değildir. Demirleri sağlamdır ve kolay taşınır. "
        "Yeşil beyaz çizgili deseniyle çok şık durur. Bagajda yer kaplamaz."
    ),
    "features": [
        "Katlanabilir Tasarım",
        "Gerçek Ahşap Kolçak",
        "Paslanmaz Metal Profil",
        "110 kg Taşıma Kapasitesi",
        "Su İtici Oxford Kumaş",
    ],
    "variants": [
        {"name": "Yeşil - Beyaz Çizgili", "price": 549.90, "price_delta": 0.0},
        {"name": "Mavi - Beyaz Çizgili", "price": 549.90, "price_delta": 0.0},
    ],
    "seo_tone": "casual",
    "rating": None,
    "review_count": None,
}

TARGET_PLATFORM = "trendyol"

def _save_json(output_dir: Path, filename: str, data: object) -> None:
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  saved → {path.name}")

def _tr(result: ToolResult) -> dict:
    return {
        "success": result.success,
        "fallback_used": result.fallback_used,
        "data": result.data,
    }

def _to_tool_results(dicts: list[dict]) -> list[ToolResult]:
    return [
        ToolResult(
            success=d.get("success", False),
            data=d.get("data") or {},
            fallback_used=d.get("fallback_used", False),
        )
        for d in dicts
    ]

async def _run_imagen_local(image_path: Path, prompt: str) -> bytes | None:
    from google import genai
    from google.genai import types
    from google.genai.types import HttpOptions

    client = genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        http_options=HttpOptions(api_version="v1"),
    )
    image_bytes = image_path.read_bytes()
    loop = asyncio.get_running_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: client.models.edit_image(
                    model=settings.imagen_model,
                    prompt=prompt,
                    reference_images=[
                        types.RawReferenceImage(
                            reference_image=types.Image(image_bytes=image_bytes),
                            reference_id=1,
                        ),
                        types.MaskReferenceImage(
                            reference_id=2,
                            config=types.MaskReferenceConfig(
                                mask_mode="MASK_MODE_BACKGROUND",
                            ),
                        ),
                    ],
                    config=types.EditImageConfig(
                        edit_mode="EDIT_MODE_BGSWAP",
                        number_of_images=1,
                    ),
                ),
            ),
            timeout=90,
        )
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
        print("  Imagen returned no images")
        return None
    except asyncio.TimeoutError:
        print("  Imagen timed out")
        return None
    except Exception as exc:
        print(f"  Imagen failed: {exc}")
        return None

async def main(image_path: Path | None) -> None:
    seed_seo_chunks()

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(__file__).parent / "test_outputs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  E2E Test  |  {run_id}")
    print(f"  Platform  : {TARGET_PLATFORM}")
    print(f"  Product   : {USER_PRODUCT['title']}")
    print(f"  Image     : {image_path or 'not provided — image step will be skipped'}")
    print(f"  Output    : {output_dir}")
    print(f"{sep}\n")

    print("── Models ────────────────────────────────────────────────────")
    for key in (
        "RIVAL_DISCOVERY_MODEL",
        "RIVAL_RESEARCH_MODEL",
        "RIVAL_SENTIMENT_MODEL",
        "RIVAL_TRENDS_MODEL",
        "RIVAL_MARKET_GAP_MODEL",
        "RIVAL_PRICING_MODEL",
        "SEO_OPTIMIZER_MODEL",
    ):
        print(f"  {key}={os.environ.get(key, '(default)')}")
    print("─────────────────────────────────────────────────────────────\n")

    timing: dict[str, float] = {}
    total_start = time.perf_counter()

    print("[1/8] competitor_discovery")
    t0 = time.perf_counter()
    discovery = await run_competitor_discovery_tool(
        platform=TARGET_PLATFORM,
        category=USER_PRODUCT["category"],
        product_title=USER_PRODUCT["title"],
        brand=USER_PRODUCT["brand"],
    )
    timing["01_discovery"] = round(time.perf_counter() - t0, 2)
    print(f"  success={discovery.success}  fallback={discovery.fallback_used}  elapsed={timing['01_discovery']}s")
    _save_json(output_dir, "01_discovery.json", _tr(discovery))

    competitor_names: list[dict] = []
    if discovery.success and discovery.data:
        competitor_names = discovery.data.get("competitors", [])
        print(f"  found {len(competitor_names)} competitors")
    else:
        print("  WARNING: discovery failed — downstream tools receive empty list")

    print("\n[2/8] competitor_research")
    t0 = time.perf_counter()
    research_results = await run_competitor_research_tool(
        competitors=competitor_names,
        category=USER_PRODUCT["category"],
    )
    timing["02_research"] = round(time.perf_counter() - t0, 2)
    ok = sum(1 for r in research_results if r.success)
    print(f"  success={ok}/{len(research_results)}  elapsed={timing['02_research']}s")
    _save_json(output_dir, "02_research.json", [_tr(r) for r in research_results])

    research_dicts = [_tr(r) for r in research_results]

    print("\n[3+4/8] sentiment_analysis + trend_analysis  (parallel)")
    t0 = time.perf_counter()
    sentiment_obj, trend_obj = await asyncio.gather(
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
    timing["03_04_sentiment_trend_parallel"] = round(time.perf_counter() - t0, 2)
    print(f"  sentiment: success={sentiment_obj.success}  fallback={sentiment_obj.fallback_used}")
    print(f"  trend:     success={trend_obj.success}  fallback={trend_obj.fallback_used}")
    print(f"  elapsed={timing['03_04_sentiment_trend_parallel']}s  (concurrent)")
    _save_json(output_dir, "03_sentiment.json", _tr(sentiment_obj))
    _save_json(output_dir, "04_trend.json", _tr(trend_obj))

    sentiment_data = sentiment_obj.data if sentiment_obj.success else {}
    trend_data = trend_obj.data if trend_obj.success else {}

    print("\n[5/8] market_gap_analyzer")
    t0 = time.perf_counter()
    gap = await run_market_gap_analyzer(
        user_product=USER_PRODUCT,
        competitor_tool_results=_to_tool_results(research_dicts),
        sentiment_result=sentiment_data,
        trend_result=trend_data,
    )
    timing["05_market_gap"] = round(time.perf_counter() - t0, 2)
    print(f"  success={gap.success}  fallback={gap.fallback_used}  elapsed={timing['05_market_gap']}s")
    _save_json(output_dir, "05_market_gap.json", _tr(gap))

    print("\n[6/8] smart_pricing_engine")
    t0 = time.perf_counter()
    pricing = await run_smart_pricing_engine(
        user_product=USER_PRODUCT,
        competitor_tool_results=_to_tool_results(research_dicts),
        gap_result=gap.data if gap.success else None,
        sentiment_result=sentiment_data,
        trend_result=trend_data,
        target_platform=TARGET_PLATFORM,
    )
    timing["06_pricing"] = round(time.perf_counter() - t0, 2)
    print(f"  success={pricing.success}  fallback={pricing.fallback_used}  elapsed={timing['06_pricing']}s")
    _save_json(output_dir, "06_pricing.json", _tr(pricing))

    rival_json = {
        "user_product": USER_PRODUCT,
        "target_platform": TARGET_PLATFORM,
        "competitors": competitor_names,
        "competitor_research_results": research_dicts,
        "sentiment_result": sentiment_data,
        "trend_result": trend_data,
        "gap_result": gap.data if gap.success else {},
        "pricing_result": pricing.data if pricing.success else {},
    }

    print("\n[7+8/8] seo_optimizer + image_generation  (parallel)")
    t0 = time.perf_counter()

    async def _run_seo() -> ToolResult:
        tool = SeoOptimizerTool()
        return await tool.run(
            SeoOptimizerInput(
                rival_json=rival_json,
                target_platform=TARGET_PLATFORM,
                user_product=USER_PRODUCT,
            )
        )

    async def _run_image() -> tuple[ToolResult, bytes | None]:
        if image_path is None:
            return (
                ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"generated_image_url": None, "error": "no image provided"},
                ),
                None,
            )
        chosen_variant = select_variant(USER_PRODUCT, rival_json.get("pricing_result", {}))
        prompt = build_image_prompt(
            user_product=USER_PRODUCT,
            selected_variant=chosen_variant,
            gap_result=rival_json.get("gap_result", {}),
            target_platform=TARGET_PLATFORM,
        )
        img_bytes = await _run_imagen_local(image_path, prompt)
        if img_bytes is None:
            return (
                ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"generated_image_url": None, "error": "Imagen returned no output"},
                ),
                None,
            )
        local_png = output_dir / "generated_image.png"
        local_png.write_bytes(img_bytes)
        return (
            ToolResult(
                success=True,
                fallback_used=False,
                data={"generated_image_url": str(local_png), "selected_variant": chosen_variant},
            ),
            img_bytes,
        )

    (seo_result, (image_result, _)) = await asyncio.gather(_run_seo(), _run_image())

    timing["07_08_seo_image_parallel"] = round(time.perf_counter() - t0, 2)
    print(f"  seo:   success={seo_result.success}  fallback={seo_result.fallback_used}")
    print(f"  image: success={image_result.success}  fallback={image_result.fallback_used}")
    print(f"  elapsed={timing['07_08_seo_image_parallel']}s  (concurrent)")
    _save_json(output_dir, "07_seo_output.json", _tr(seo_result))
    _save_json(output_dir, "08_image_output.json", _tr(image_result))
    if image_result.success:
        print(f"  image  saved → generated_image.png")

    timing["TOTAL"] = round(time.perf_counter() - total_start, 2)

    total = {
        "run_id": run_id,
        "user_product": USER_PRODUCT,
        "target_platform": TARGET_PLATFORM,
        "rival": {
            "competitor_names": competitor_names,
            "competitor_research_results": research_dicts,
            "sentiment_result": sentiment_data,
            "trend_result": trend_data,
            "gap_result": gap.data if gap.success else {},
            "pricing_result": pricing.data if pricing.success else {},
        },
        "seo": {
            "seo_output": seo_result.data if seo_result.success else {},
            "generated_image_url": image_result.data.get("generated_image_url"),
        },
        "timing": timing,
    }

    print("\n[Final] Saving total.json and timing.json")
    _save_json(output_dir, "total.json", total)
    _save_json(output_dir, "timing.json", timing)

    print(f"\n{sep}")
    print("  Timing Summary")
    print(f"{sep}")
    for step, elapsed in timing.items():
        if step == "TOTAL":
            continue
        bar = "█" * int(elapsed / timing["TOTAL"] * 30)
        print(f"  {step:<38} {elapsed:>6.2f}s  {bar}")
    print(f"{'─' * 62}")
    print(f"  {'TOTAL':<38} {timing['TOTAL']:>6.2f}s")
    print(f"{sep}")
    print(f"\n  All outputs → {output_dir}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E test for Rival + SEO pipeline")
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Local product image path for Imagen (PNG/JPG). Skipped if not provided.",
    )
    args = parser.parse_args()

    image = args.image or LOCAL_IMAGE_PATH

    if image and not image.exists():
        print(f"ERROR: image file not found: {image}")
        sys.exit(1)

    asyncio.run(main(image))
