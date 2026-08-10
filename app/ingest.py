"""
Loads every .md/.txt/.pdf file in data/sample_notes, splits it into
chunks, embeds each chunk, and stores the result in a persistent
Chroma collection on disk.

Run this once whenever the notes change:
    python -m app.ingest
"""
import os

from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from app.config import NOTES_DIR, CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL


def load_documents():
    """Load all supported files from sample_notes into LangChain Documents."""
    docs = []

    for glob, loader_cls in [
        ("**/*.md", TextLoader),
        ("**/*.txt", TextLoader),
        ("**/*.pdf", PyPDFLoader),
        ("**/*.docx", Docx2txtLoader),
    ]:
        loader = DirectoryLoader(NOTES_DIR, glob=glob, loader_cls=loader_cls)
        loaded = loader.load()
        print(f"  {glob}: {len(loaded)} document(s)")
        docs.extend(loader.load())

    return docs


def chunk_documents(docs):
    """Splitting long documents into overlapping chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)


def build_index(batch_size: int = 100, reset: bool = True):
    """Building the index, creating chunks and embedding it as vectors in the ChromaDB."""
    docs = load_documents()
    if not docs:
        print(f"No documents found in {NOTES_DIR}. Add some notes first.")
        return

    chunks = chunk_documents(docs)
    print(f"Loaded {len(docs)} document(s) -> split into {len(chunks)} chunk(s)")

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    os.makedirs(CHROMA_DIR, exist_ok=True)

    if reset:
        import shutil
        if os.path.exists(CHROMA_DIR):
            shutil.rmtree(CHROMA_DIR)
            os.makedirs(CHROMA_DIR)
            print("Cleared existing index before rebuilding.")

    vectordb = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectordb.add_documents(batch)
        print(f"  embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")

    print(f"Indexed into Chroma at {CHROMA_DIR} (collection: {COLLECTION_NAME})")
    return vectordb


if __name__ == "__main__":
    build_index()