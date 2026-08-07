import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ollama models — pull these first: `ollama pull llama3.2` and
# `ollama pull nomic-embed-text`
LLM_MODEL = os.getenv("LEARNMATE_LLM_MODEL", "llama3.2")
EMBED_MODEL = os.getenv("LEARNMATE_EMBED_MODEL", "nomic-embed-text")

# This is where the raw study material lives (md, txt, pdf)
NOTES_DIR = os.path.join(BASE_DIR, "data", "sample_notes")

# Chroma persists its index to disk here so you don't re-embed every run
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")
COLLECTION_NAME = "learnmate_notes"

# Simple local "database" for quiz score history
SCORES_FILE = os.path.join(BASE_DIR, "data", "scores.json")

# Defaulted to one user currently
DEFAULT_STUDENT_ID = "default_student"