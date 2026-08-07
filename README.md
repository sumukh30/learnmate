# 📚 LearnMate

> 🚧 **Work in progress** — actively being built, day by day. Not production-ready yet. Expect rough edges, missing pieces, and things that will change.

An adaptive study copilot that lets you **ask doubts on your own notes** and **get quizzed** on them — with quiz difficulty that adapts based on how you've done before.

Built as a hands-on learning project to understand RAG, agents, and LangGraph by actually building with them — not just reading about them.

## ✨ What it does (or will do)

- 🧠 **Doubt-clearing (RAG)**: Ask "why," "how," or "when" questions about your own uploaded notes/textbook and get answers grounded in _your_ material, with source citations.
- 📝 **Quiz generation (Agent)**: Ask to be quizzed on a topic and get exam-style practice questions generated from your actual notes.
- 📈 **Adaptive difficulty**: The agent tracks what you get wrong and leans into weak topics on future quizzes.

## 🛠️ Tech stack

- [LangChain](https://www.langchain.com/) + [LangGraph](https://www.langchain.com/langgraph) - orchestration and agent logic
- [Chroma](https://www.trychroma.com/) - vector database for retrieval
- [Ollama](https://ollama.com) - running local open-source LLMs (Llama 3.2)
- FastAPI - API layer _(coming soon)_
- React - frontend _(stretch goal)_

## 🚦 Status

| Piece                       | Status         |
| --------------------------- | -------------- |
| Ingestion + retrieval (RAG) | 🟡 in progress |
| LangGraph state machine     | 🟡 in progress |
| Agent tools (quiz, scoring) | 🟡 in progress |
| FastAPI endpoints           | ⚪ not started |
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

3. Add notes to `data/sample_notes/`, then build the index:

```bash
   python -m app.ingest
```

4. Run it:

```bash
   python -m app.graph
```

## 🗺️ Architecture

A single LangGraph classifies intent, then routes to one of three branches: answer a doubt (retrieve → answer), generate a quiz (check history → retrieve → generate), or log a quiz result. Details in the code — architecture diagram coming as the project matures.

## 📄 License

MIT - see [LICENSE](./LICENSE).
