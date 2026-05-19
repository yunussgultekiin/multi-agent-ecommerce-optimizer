from .prompts_seo import TONE_DIRECTIVES
from app.config import settings
import logging

logger = logging.getLogger(__name__)

PLATFORM_DEFAULT_TONE: dict[str, str] = {
    "trendyol": "casual",
    "amazon": "professional",
    "hepsiburada": "professional",
}

def query_chroma(target_platform: str, category: str) -> list[str]:
    try:
        from app.chroma_client import get_seo_collection

        collection = get_seo_collection()
        total_count = collection.count()
        if total_count == 0:
            logger.info("SEO ChromaDB collection is empty, skipping RAG")
            return []

        query = (
            f"{target_platform} {category} SEO başlık açıklama keyword optimizasyonu"
        )
        top_k = min(settings.chroma_top_k, total_count)

        where_filter = (
            {
                "$or": [
                    {"platform": {"$eq": target_platform}},
                    {"platform": {"$eq": "general"}},
                ]
            }
            if target_platform != "general"
            else {"platform": {"$eq": "general"}}
        )

        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
            )
        except Exception:
            results = collection.query(query_texts=[query], n_results=top_k)

        docs: list[str] = results.get("documents", [[]])[0]
        logger.info(
            "ChromaDB RAG query returned %d chunks | platform=%s category=%s",
            len(docs),
            target_platform,
            category,
        )
        return docs

    except ImportError:
        logger.warning("chromadb not available, skipping RAG")
        return []
    except Exception as exc:
        logger.warning("ChromaDB query failed, proceeding without RAG | error=%s", exc)
        return []


def resolve_tone(user_product: dict, target_platform: str) -> str:
    seo_tone = user_product.get("seo_tone", "")
    if seo_tone in TONE_DIRECTIVES:
        return seo_tone
    return PLATFORM_DEFAULT_TONE.get(target_platform, "professional")

def log_seo_tool_call(
    target_platform: str,
    seo_tone: str,
    title_char_count: int,
    meta_word_count: int,
    keyword_gap_count: int,
    variant_seo_count: int,
    rag_context_count: int,
    title_within_limit: bool,
    fallback_used: bool,
) -> None:
    logger.info(
        "SeoOptimizerTool completed | target_platform=%s seo_tone=%s title_char_count=%d "
        "meta_word_count=%d keyword_gap_count=%d variant_seo_count=%d "
        "rag_context_count=%d title_within_limit=%s fallback_used=%s",
        target_platform,
        seo_tone,
        title_char_count,
        meta_word_count,
        keyword_gap_count,
        variant_seo_count,
        rag_context_count,
        title_within_limit,
        fallback_used,
    )
