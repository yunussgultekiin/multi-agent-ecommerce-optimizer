from .models_seo import SeoOptimizerInput, SeoOutput
from .prompts_seo import PLATFORM_TITLE_LIMITS, build_seo_prompt
from .utils_seo import log_seo_tool_call, query_chroma, resolve_tone
from app.core import ToolResult, WorkflowError
from app.gemini_correction import GeminiCorrectionLoop
import asyncio
import logging

logger = logging.getLogger(__name__)

class SeoOptimizerTool:
    def __init__(self) -> None:
        self._correction_loop = GeminiCorrectionLoop()

    async def run(self, input_data: SeoOptimizerInput) -> ToolResult:
        user_product = input_data.user_product
        target_platform = input_data.target_platform
        category = user_product.get("category", "")
        seo_tone_raw = user_product.get("seo_tone", "")

        loop = asyncio.get_running_loop()
        rag_chunks = await loop.run_in_executor(None, query_chroma, target_platform, category)
        tone_key = resolve_tone(user_product, target_platform)

        prompt = build_seo_prompt(
            user_product=user_product,
            rival_json=input_data.rival_json,
            platform=target_platform,
            rag_chunks=rag_chunks,
            tone_key=tone_key,
        )

        try:
            result: SeoOutput = await self._correction_loop.generate_and_validate(
                prompt=prompt,
                output_model=SeoOutput,
            )
        except WorkflowError as exc:
            logger.error(
                "SeoOptimizerTool self-correction exhausted | platform=%s error=%s",
                target_platform,
                exc,
            )
            return ToolResult(
                success=False, fallback_used=True, data={"error": str(exc)}
            )
        except Exception as exc:
            logger.error(
                "SeoOptimizerTool unexpected error | platform=%s error=%s",
                target_platform,
                exc,
            )
            return ToolResult(
                success=False, fallback_used=True, data={"error": str(exc)}
            )

        title_limit = PLATFORM_TITLE_LIMITS.get(target_platform, 200)
        title_char_count = len(result.title_suggestion)
        meta_word_count = len(result.meta_description.split())

        log_seo_tool_call(
            target_platform=target_platform,
            seo_tone=seo_tone_raw or f"platform_default:{tone_key}",
            title_char_count=title_char_count,
            meta_word_count=meta_word_count,
            keyword_gap_count=len(result.keyword_gaps),
            variant_seo_count=len(result.variant_seo),
            rag_context_count=len(rag_chunks),
            title_within_limit=title_char_count <= title_limit,
            fallback_used=False,
        )

        return ToolResult(success=True, data=result.model_dump(), fallback_used=False)
