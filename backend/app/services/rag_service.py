from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import chromadb
import google.generativeai as genai

from app.config import settings

# --- Gemini embedding config ---
if not settings.gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

genai.configure(api_key=settings.gemini_api_key)

# Gemini text-embedding model
EMBEDDING_MODEL = "text-embedding-004"

# --- Paths for KB and Chroma ---
BASE_DIR = Path(__file__).resolve().parents[1]  # .../app
KB_DIR = BASE_DIR / "kb"                        # .../app/kb
CHROMA_DIR = BASE_DIR / "chroma_db"             # .../app/chroma_db

CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# --- ChromaDB client / collection setup ---
client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Name must be 3–512 chars, alphanumeric / . _ -
collection = client.get_or_create_collection(name="support_kb")


# ---------- Embedding ----------

def embed_text(text: str) -> List[float]:
    """
    Use Gemini to get an embedding vector for a piece of text.
    """
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
    )
    # google-generativeai returns a dict with key "embedding"
    return result["embedding"]  # type: ignore[no-any-return]


# ---------- KB loading & chunking ----------

def _simple_chunk(text: str, max_chars: int = 800) -> List[str]:
    """
    Very basic chunking: split text into ~max_chars chunks on paragraph boundaries.
    Good enough for a course project.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            # keep adding to current chunk
            current = f"{current}\n\n{para}".strip()
        else:
            # push current and start new
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    # Fallback: if file is tiny, ensure at least one chunk
    if not chunks and text.strip():
        chunks.append(text.strip())

    return chunks


def _load_kb_files() -> List[Dict[str, Any]]:
    """
    Load all .md and .txt files from the kb folder.
    """
    docs: List[Dict[str, Any]] = []
    if not KB_DIR.exists():
        return docs

    for path in KB_DIR.glob("**/*"):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            # Ignore unreadable files
            continue

        docs.append(
            {
                "id": path.stem,   # base name without extension
                "path": str(path),
                "text": text,
            }
        )
    return docs


def ensure_kb_indexed() -> None:
    """
    Index KB documents into Chroma if not already present.
    For this course project we keep it simple:
    - If the collection already has vectors, we assume it is indexed.
    - Otherwise, we read all kb/*.md, *.txt and embed them.
    """
    try:
        if collection.count() > 0:
            # Already indexed; skip re-indexing
            return
    except Exception:
        # If count is not supported for some reason, we'll just continue
        pass

    kb_docs = _load_kb_files()
    if not kb_docs:
        return

    new_ids: List[str] = []
    new_docs: List[str] = []
    new_metas: List[Dict[str, Any]] = []
    new_embs: List[List[float]] = []

    for doc in kb_docs:
        base_id = doc["id"]
        chunks = _simple_chunk(doc["text"])
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{base_id}::chunk{idx}"

            new_ids.append(chunk_id)
            new_docs.append(chunk)
            new_metas.append(
                {
                    "source": doc["path"],
                    "base_id": base_id,
                    "chunk_index": idx,
                }
            )
            new_embs.append(embed_text(chunk))

    if new_ids:
        collection.add(
            ids=new_ids,
            documents=new_docs,
            metadatas=new_metas,
            embeddings=new_embs,
        )


# Run indexing once at import time (simple, dev-friendly)
ensure_kb_indexed()


# ---------- Retrieval API used by chatbot ----------

def retrieve_relevant_chunks(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Given a user query, return top-n relevant KB chunks with metadata.
    If the collection is empty or anything fails, return [] so caller can fall back.
    """
    try:
        if collection.count() == 0:
            return []
    except Exception:
        # If count not available or Chroma has an issue, fail gracefully
        return []

    query_emb = embed_text(query)

    result = collection.query(
        query_embeddings=[query_emb],
        n_results=n_results,
    )

    if not result or not result.get("documents"):
        return []

    docs = result["documents"][0]
    metas = result["metadatas"][0]
    distances = result["distances"][0]

    out: List[Dict[str, Any]] = []
    for text, meta, dist in zip(docs, metas, distances):
        out.append(
            {
                "text": text,
                "metadata": meta,
                "distance": dist,
            }
        )
    return out
