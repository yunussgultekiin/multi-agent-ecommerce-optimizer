import asyncio
import json
import logging
import re
import google.auth.exceptions
import google.api_core.exceptions
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from app.config import settings
from app.core import ToolResult

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)


class VariantSeo(BaseModel):
    variant_name: str
    title_suggestion: str
    keywords: list[str] = Field(default_factory=list)


class SeoOutput(BaseModel):
    title_suggestion: str = Field(..., min_length=1)
    meta_description: str = Field(..., min_length=1)
    content_recommendations: list[str] = Field(..., min_length=1)
    keyword_gaps: list[str] = Field(..., min_length=1)
    backlink_suggestions: list[str] = Field(default_factory=list)
    competitor_comparison_summary: str = Field(..., min_length=1)
    platform_specific_tips: list[str] = Field(..., min_length=1)
    variant_seo: list[VariantSeo] = Field(default_factory=list)


class SeoOptimizerInput(BaseModel):
    rival_json: dict
    rag_context: list[str]
    target_platform: str


def _build_prompt(input: SeoOptimizerInput) -> str:
    rival_json = input.rival_json
    user_product = rival_json.get("user_product", {})
    gap_result = rival_json.get("gap_result", {})
    pricing_result = rival_json.get("pricing_result", {})
    platform = input.target_platform

    competitor_lines = []
    for r in rival_json.get("competitor_research_results", [])[:3]:
        data = r.get("data", {}) if isinstance(r, dict) else {}
        name = data.get("competitor_name", "")
        features = data.get("features", [])[:3]
        keywords = data.get("trending_keywords", [])[:3]
        if name:
            competitor_lines.append(f"- {name}: features={features}, trending_keywords={keywords}")

    variants = user_product.get("variants", [])
    variant_names = [v.get("name", "") for v in variants if isinstance(v, dict) and v.get("name")]

    gap_opportunities = gap_result.get("gap_opportunities", [])[:4]
    positioning = pricing_result.get("positioning", "unknown")
    market_power_gap = pricing_result.get("market_power_gap", "")

    rag_block = "\n".join(input.rag_context)

    return f"""You are an SEO specialist for {platform} marketplace.

USER PRODUCT:
title: {user_product.get("title", "")}
brand: {user_product.get("brand", "")}
category: {user_product.get("category", "")}
features: {user_product.get("features", [])[:5]}
variants: {variant_names}
price: {user_product.get("price")}

PLATFORM CONTEXT:
{rag_block}

COMPETITOR INSIGHTS:
{chr(10).join(competitor_lines) if competitor_lines else "No competitor data."}

MARKET GAP OPPORTUNITIES:
{gap_opportunities}

PRICING POSITION:
positioning={positioning}
market_power_gap={market_power_gap}

TASK:
Generate SEO recommendations for this product listing on {platform}.
Use gap opportunities and competitor trending keywords to find keyword gaps.
Give platform-specific tips for {platform} listing best practices.
Include variant SEO only if variants exist (use variant_names list above).
Do not invent competitor product details.

RESPOND ONLY with this JSON (no extra text):
{{
  "title_suggestion": "...",
  "meta_description": "...",
  "content_recommendations": ["..."],
  "keyword_gaps": ["..."],
  "backlink_suggestions": ["..."],
  "competitor_comparison_summary": "...",
  "platform_specific_tips": ["..."],
  "variant_seo": [{{"variant_name": "...", "title_suggestion": "...", "keywords": ["..."]}}]
}}

Rules:
- title_suggestion: max 200 chars, include brand and category
- meta_description: max 300 chars
- content_recommendations: 3-5 items
- keyword_gaps: 3-6 items
- variant_seo: one entry per variant, or empty list []
"""


def _clean_json(text: str) -> str:
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        return text[first:last + 1]
    return text


async def _call_gemini(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=settings.gemini_flash_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=1200,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            ),
        )
    except google.auth.exceptions.DefaultCredentialsError as exc:
        raise RuntimeError("Google Cloud credentials not configured.") from exc
    except google.api_core.exceptions.NotFound as exc:
        raise RuntimeError(f"Model '{settings.gemini_flash_model}' not found.") from exc
    except google.api_core.exceptions.PermissionDenied as exc:
        raise RuntimeError("Permission denied. Check Vertex AI User role.") from exc
    return response.text or ""


class SeoOptimizerTool:
    async def run(self, input: SeoOptimizerInput) -> ToolResult:
        prompt = _build_prompt(input)
        last_error = None

        for attempt in range(3):
            current_prompt = (
                f"THE PREVIOUS ATTEMPT FAILED:\n{last_error}\n\nFix and return ONLY valid JSON.\n\nORIGINAL TASK:\n{prompt}"
                if attempt > 0
                else prompt
            )

            try:
                response_text = await _call_gemini(current_prompt)
                cleaned = _clean_json(response_text)
                data = json.loads(cleaned)
                result = SeoOutput(**data)

                logger.info(
                    "SeoOptimizerTool completed | platform=%s fallback=%s",
                    input.target_platform,
                    attempt > 0,
                )

                return ToolResult(success=True, data=result.model_dump(), fallback_used=attempt > 0)

            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                logger.warning(
                    "SeoOptimizerTool attempt failed | attempt=%d error=%s",
                    attempt + 1,
                    last_error,
                )
                if attempt == 2:
                    return ToolResult(
                        success=False,
                        fallback_used=True,
                        data={"error": f"Max retries: {last_error}"},
                    )

        return ToolResult(success=False, fallback_used=True, data={"error": "Unexpected error"})
