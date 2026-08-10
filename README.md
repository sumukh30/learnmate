# 📚 LearnMate

> 🚧 **Work in progress** — actively being built, day by day. Not production-ready yet. Expect rough edges, missing pieces, and things that will change.

An adaptive study copilot that lets you **ask doubts on your own notes** and **get quizzed** on them — with quiz difficulty and topic selection that adapts based on how you've done before.

Built as a hands-on learning project to understand RAG, agents, and LangGraph by actually building with them — not just reading about them.

## ✨ What it does

- 🧠 **Doubt-clearing (RAG)** — Ask "why," "how," or "when" questions about your own uploaded notes/textbook and get answers grounded in _your_ material, with source citations.
- 📝 **Quiz generation (Agent)** — Ask to be quizzed on a topic and get 10 exam-style practice questions generated from your actual notes. No topic given? It defaults to your weakest topic automatically.
- 📈 **Adaptive difficulty** — The agent tracks what you get wrong per topic and drops difficulty on topics you're struggling with.
- 👥 **Multi-student support** — Score history is tracked per student ID, so more than one person can use the same instance without their progress mixing.

## 🛠️ Tech stack

- [LangChain](https://www.langchain.com/) + [LangGraph](https://www.langchain.com/langgraph) — orchestration and agent logic
- [Chroma](https://www.trychroma.com/) — vector database for retrieval
- [Ollama](https://ollama.com) — running local open-source LLMs (Llama 3.2)
- FastAPI — API layer _(in progress)_
- React — frontend _(in progress)_

## 🚦 Status

| Piece                       | Status         |
| --------------------------- | -------------- |
| Ingestion + retrieval (RAG) | ✅ working     |
| LangGraph state machine     | ✅ working     |
| Agent tools (quiz, scoring) | ✅ working     |
| Multi-student support       | ✅ working     |
| FastAPI endpoints           | 🟡 in progress |
| React frontend              | ⚪ not started |

## 🚀 Setup

1. Install [Ollama](https://ollama.com) and pull the models:

```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
```

2. Set up the environment:

```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
```

3. Add notes to `data/sample_notes/` (`.md`, `.txt`, `.pdf`, `.docx` supported), then build the index:

```bash
   python -m app.ingest
```

4. Run it:

```bash
   python -m app.graph
```

You'll be asked for a student ID (press enter to use a default one).

## 🗺️ Architecture

A single LangGraph classifies intent, then routes to one of three branches:

- **Doubt** → retrieve → answer, with source citation
- **Quiz** → check history → retrieve → generate (defaults topic to weakest area, defaults difficulty to medium, drops to easy on weak topics)
- **Submit answer** → log result, updates per-student, per-topic accuracy

## ⚠️ Known limitations (Day 1 scope)

- No error handling yet if Ollama isn't running — will raise a raw exception.
- Quiz generation quality depends on how well the underlying notes are chunked; sparse or poorly structured notes will produce weaker questions.
- Score history is a flat JSON file — fine for a handful of students, not built for real concurrency.

## 📄 License

MIT — see [LICENSE](./LICENSE).
