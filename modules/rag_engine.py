"""RAG (retrieval-augmented generation) engine backed by ChromaDB.

Loads JSON knowledge files from data/, chunks each entry's content with a
character-window overlap, embeds chunks via Ollama's nomic-embed-text, and
stores everything in a persistent Chroma collection for fast lookup.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import chromadb
import ollama

DATA_FILES = ["monsters.json", "spells.json", "rules.json", "world_lore.json", "items.json"]
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50
COLLECTION_NAME = "dnd_knowledge"


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character windows."""
    if size <= overlap:
        raise ValueError("chunk size must be larger than overlap")
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    step = size - overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + size]
        if not chunk:
            break
        chunks.append(chunk)
        if start + size >= len(text):
            break
    return chunks


def _embed(text: str) -> list[float]:
    """Embed a single passage using the configured Ollama embedding model."""
    response = ollama.embed(model=EMBED_MODEL, input=text)
    embeddings = response.get("embeddings") or response.get("embedding")
    if not embeddings:
        raise RuntimeError(f"Ollama returned no embedding for text of length {len(text)}")
    # ollama.embed returns either a single embedding or a list of them.
    if isinstance(embeddings[0], (int, float)):
        return list(embeddings)
    return list(embeddings[0])


class RAGEngine:
    """Persistent vector store over the project's D&D knowledge base."""

    def __init__(self, data_dir: str = "data", db_dir: str = "./chroma_db") -> None:
        """Open the Chroma collection and index data files if empty."""
        self.data_dir = Path(data_dir)
        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_dir)
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
        if self.collection.count() == 0:
            self._load_and_index()

    def _load_and_index(self) -> None:
        """Walk the data files, chunk each entry, embed, and upsert."""
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        embeddings: list[list[float]] = []
        for filename in DATA_FILES:
            path = self.data_dir / filename
            try:
                with open(path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except FileNotFoundError:
                print(f"[RAG] WARNING: missing data file {path}, skipping.")
                continue
            except json.JSONDecodeError as e:
                print(f"[RAG] ERROR: {path} is not valid JSON ({e}), skipping.")
                continue
            for entry in entries:
                entry_id = entry.get("id") or entry.get("name", "unknown")
                content = entry.get("content", "")
                if not content:
                    continue
                for i, chunk in enumerate(_chunk_text(content)):
                    chunk_id = f"{filename}:{entry_id}:{i}"
                    ids.append(chunk_id)
                    documents.append(chunk)
                    metadatas.append(
                        {
                            "source": filename,
                            "entry_id": entry_id,
                            "name": entry.get("name", entry_id),
                        }
                    )
                    embeddings.append(_embed(chunk))
        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            print(f"[RAG] indexed {len(ids)} chunks across {len(DATA_FILES)} files.")

    def query(self, text: str, n_results: int = 3) -> str:
        """Embed a query and return the top results joined as a single string."""
        if not text.strip():
            return ""
        try:
            embedding = _embed(text)
            result = self.collection.query(query_embeddings=[embedding], n_results=n_results)
        except Exception as e:
            print(f"[RAG] query failed: {e}")
            return ""
        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        if not documents or not documents[0]:
            return ""
        lines: list[str] = []
        for doc, meta in zip(documents[0], metadatas[0]):
            label = meta.get("name", meta.get("entry_id", "ref"))
            lines.append(f"[{label}] {doc}")
        return "\n".join(lines)
