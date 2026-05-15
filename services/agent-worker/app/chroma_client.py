import json
import logging
from pathlib import Path
import chromadb
from app.config import settings

logger = logging.getLogger(__name__)
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "seo_chunks.json"
_chroma_client: chromadb.ClientAPI | None = None
_seo_collection = None

def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.EphemeralClient()
    return _chroma_client


def get_seo_collection():
    global _seo_collection
    if _seo_collection is None:
        client = get_chroma_client()
        _seo_collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _seo_collection


def seed_seo_chunks() -> None:
    try:
        if not _DATA_PATH.exists():
            logger.warning("seo_chunks.json not found at %s — skipping seed", _DATA_PATH)
            return

        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        collection = get_seo_collection()
        if collection.count() == len(chunks):
            logger.info(
                "SEO ChromaDB already up-to-date | count=%d collection=%s",
                len(chunks),
                settings.chroma_collection_name,
            )
            return

        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [{"platform": c["platform"], "topic": c["topic"]} for c in chunks]

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(
            "SEO ChromaDB seeded | chunk_count=%d collection=%s",
            len(chunks),
            settings.chroma_collection_name,
        )

    except Exception as exc:
        logger.warning(
            "SEO ChromaDB seed failed — proceeding without RAG | error=%s", exc
        )
