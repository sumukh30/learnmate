"""
Thin wrapper around the Chroma vector store so the rest of the app
never has to know embedding/DB details — it just calls retrieve(query).
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from app.config import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL

_vectordb = None


def _get_vectordb():
    global _vectordb
    if _vectordb is None:
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        _vectordb = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
    return _vectordb


def retrieve(query: str, k: int = 5, topic: str | None = None) -> list[dict]:
    """
    Return the top-k most relevant chunks for a query as a list of
    {"text": ..., "source": ...} dicts. If a `topic` is given, it is
    used instead of the raw query which is useful for quiz generation where
    we search by topic name rather than a question.
    """
    search_query = topic if topic else query
    vectordb = _get_vectordb()
    results = vectordb.similarity_search(search_query, k=k)

    return [
        {
            "text": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
        }
        for doc in results
    ]


if __name__ == "__main__":
    hits = retrieve("generalization and overfitting")
    for i, h in enumerate(hits, 1):
        print(f"--- chunk {i} ({h['source']}) ---")
        print(h["text"][:200], "...\n")