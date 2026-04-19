"""
StudyCraft – RAG index (ChromaDB + MiniLM).

Indexes the full document text so each chapter generation can retrieve
the most relevant chunks as grounding context.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()

_EMBED_MODEL = "all-MiniLM-L6-v2"
_COLLECTION = "studycraft_doc"


class RAGIndex:
    def __init__(self, persist_dir: str | Path = "./rag_index") -> None:
        from chromadb import PersistentClient
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        self._client = PersistentClient(path=str(persist_dir))
        self._ef = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
        self._col = self._client.get_or_create_collection(
            name=_COLLECTION,
            embedding_function=self._ef,
        )

    def index(self, text: str, source_name: str = "document") -> int:
        """Chunk and index arbitrary text. Returns number of chunks added."""
        chunks = self._chunk(text)
        if not chunks:
            return 0

        ids = [f"{source_name}_{i}" for i in range(len(chunks))]

        # Delete old entries for this source to avoid duplication on re-runs
        try:
            existing = self._col.get(where={"source": source_name})
            if existing["ids"]:
                self._col.delete(ids=existing["ids"])
        except Exception:
            pass

        self._col.add(
            documents=chunks,
            ids=ids,
            metadatas=[{"source": source_name}] * len(chunks),
        )
        console.print(f"  [cyan]✓ RAG:[/cyan] indexed {len(chunks)} chunks from '{source_name}'")
        return len(chunks)

    def query(self, topic: str, n_results: int = 4) -> str:
        """Return the top-n most relevant chunks joined as a single string."""
        try:
            res = self._col.query(query_texts=[topic], n_results=n_results)
            docs = res.get("documents", [[]])[0]
            return "\n\n---\n\n".join(docs) if docs else ""
        except Exception:
            return ""

    def clear(self) -> None:
        """Wipe the entire index (useful between different documents)."""
        try:
            self._client.delete_collection(_COLLECTION)
        except Exception:
            pass
        # Re-create empty
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        self._ef = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
        self._col = self._client.get_or_create_collection(
            name=_COLLECTION,
            embedding_function=self._ef,
        )

    # ── Chunker ───────────────────────────────────────────────────────────────

    @staticmethod
    def _chunk(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
        """Sliding-window word chunker with overlap."""
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + size])
            if chunk.strip():
                chunks.append(chunk)
            i += size - overlap
        return chunks
