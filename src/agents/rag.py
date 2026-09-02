"""Hybrid RAG over policy markdown: vector (Chroma) + keyword (same chunks).
No PDF loader, no GPT."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb

ROOT = Path(__file__).resolve().parents[2]
POLICIES = ROOT / "policies"
CHROMA_DIR = ROOT / "data" / "chroma_db"


class EmbeddingManager:
    """Document embeddings via sentence-transformers (same model as the notebook)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        print(f"Loading model: {self.model_name}")
        self.model = SentenceTransformer(model_name)

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        if not self.model:
            raise ValueError("model not loaded")
        print(f"Generating embeddings for {len(texts)} texts...")
        return self.model.encode(texts, show_progress_bar=True)


_CHROMA_BY_PATH: dict[str, object] = {}


def _chroma_client(path: str):
    """One PersistentClient per path. Survives uvicorn --reload half-dead systems."""
    if path in _CHROMA_BY_PATH:
        return _CHROMA_BY_PATH[path]
    try:
        client = chromadb.PersistentClient(path=path)
    except Exception:
        # Hot-reload leaves a broken SharedSystemClient; clear and retry once.
        from chromadb.api.client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
        client = chromadb.PersistentClient(path=path)
    _CHROMA_BY_PATH[path] = client
    return client


class VectorStoreManager:
    """Persistent Chroma index + similarity search."""

    def __init__(
        self,
        collection_name: str = "finoptima_policies",
        persist_dir: str | None = None,
    ) -> None:
        path = persist_dir or str(CHROMA_DIR)
        self.client = _chroma_client(path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        print(f"Chroma collection '{collection_name}' at '{path}' ({self.collection.count()} docs)")

    def add_documents(self, chunks: List[dict], embedding_manager: EmbeddingManager) -> None:
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [f"rule_{i}_{uuid.uuid4().hex[:6]}" for i in range(len(chunks))]
        embeddings = embedding_manager.generate_embeddings(texts)
        self.collection.add(
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
            ids=ids,
        )
        print(f"Indexed {len(chunks)} rule chunks")

    def search(
        self,
        query: str,
        embedding_manager: EmbeddingManager,
        n_results: int = 3,
    ) -> dict:
        query_embedding = embedding_manager.generate_embeddings([query])
        return self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
        )


def load_rule_chunks() -> List[dict]:
    """One chunk per ### Rule heading (not 1000-char PDF splits)."""
    chunks: List[dict] = []
    for path in sorted(POLICIES.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        parts = text.split("### ")
        for part in parts:
            part = part.strip()
            if not part.startswith("Rule"):
                continue
            first_line = part.splitlines()[0]
            chunks.append(
                {
                    "text": "### " + part,
                    "metadata": {
                        "source_file": path.name,
                        "rule_heading": first_line[:200],
                    },
                }
            )
    print(f"Loaded {len(chunks)} rule chunks from {POLICIES}")
    return chunks


def tokenize(text: str) -> set[str]:
    """Lowercase word/number tokens. Cheap lexical index — no model."""
    return set(re.findall(r"[a-z0-9$%]+", text.lower()))


def keyword_search(query: str, chunks: List[dict], n_results: int = 3) -> List[dict]:
    """Vectorless: rank the same Rule cards by shared tokens."""
    query_tokens = tokenize(query)
    scored: List[tuple[int, dict]] = []
    for chunk in chunks:
        overlap = query_tokens & tokenize(chunk["text"])
        if not overlap:
            continue
        scored.append((len(overlap), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _score, chunk in scored[:n_results]]


def hybrid_search(
    query: str,
    chunks: List[dict],
    store: VectorStoreManager,
    embedder: EmbeddingManager,
    n_results: int = 3,
) -> List[dict]:
    """Run vector + keyword on the same cards; merge unique Rules."""
    vector_raw = store.search(query, embedder, n_results=n_results)
    vector_hits: List[dict] = []
    for doc, meta in zip(vector_raw["documents"][0], vector_raw["metadatas"][0]):
        vector_hits.append({"text": doc, "metadata": meta, "via": "vector"})

    keyword_hits = keyword_search(query, chunks, n_results=n_results)

    merged: List[dict] = []
    seen: set[str] = set()
    for hit in vector_hits:
        key = str(hit["metadata"].get("rule_heading", ""))
        seen.add(key)
        merged.append(hit)
    for chunk in keyword_hits:
        key = str(chunk["metadata"].get("rule_heading", ""))
        if key in seen:
            for hit in merged:
                if str(hit["metadata"].get("rule_heading", "")) == key:
                    hit["via"] = "both"
                    break
            continue
        seen.add(key)
        merged.append({"text": chunk["text"], "metadata": chunk["metadata"], "via": "keyword"})
    return merged


_INDEX = None


def get_index() -> tuple[list[dict], VectorStoreManager, EmbeddingManager]:
    """Build Chroma once per process. Do not wipe the collection."""
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    chunks = load_rule_chunks()
    embedder = EmbeddingManager()
    store = VectorStoreManager()
    if store.collection.count() == 0:
        store.add_documents(chunks, embedder)
    _INDEX = (chunks, store, embedder)
    return _INDEX


def retrieve_rules(query: str, n_results: int = 3) -> List[dict]:
    chunks, store, embedder = get_index()
    hits = hybrid_search(query, chunks, store, embedder, n_results=n_results)
    return [
        {
            "heading": str(h["metadata"].get("rule_heading", "")),
            "source": str(h["metadata"].get("source_file", "")),
            "text": h["text"][:800],
            "via": h.get("via", ""),
        }
        for h in hits
    ]


def main() -> None:
    chunks = load_rule_chunks()
    embedder = EmbeddingManager()
    store = VectorStoreManager()
    store.add_documents(chunks, embedder)

    queries = [
        "cloud budget variance more than 15 percent and dollar overrun over 5000 mitigation plan",
        "subscription zero logins 30 consecutive days audit evidence workpaper",
        "procurement cancellation queue idle product before next invoice",
    ]
    for query in queries:
        print(f"\n--- QUERY: {query} ---")
        hits = hybrid_search(query, chunks, store, embedder, n_results=3)
        for i, hit in enumerate(hits):
            meta = hit["metadata"]
            heading = str(meta.get("rule_heading", "")).encode("ascii", "replace").decode()
            snippet = hit["text"][:400].encode("ascii", "replace").decode()
            print(f"\n[{i + 1}] via={hit['via']} | {meta.get('source_file')} | {heading}")
            print(snippet)
            print("---")


if __name__ == "__main__":
    main()
