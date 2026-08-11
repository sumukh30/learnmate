# 📚 LearnMate

> 🚧 **Work in progress** — actively being built, day by day. Not production-ready yet. Expect rough edges, missing pieces, and things that will change.

An adaptive study copilot that lets you **ask doubts on your own notes** and **get quizzed** on them — with quiz difficulty and topic selection that adapts based on how you've done before.

Built as a hands-on learning project to understand RAG, agents, and LangGraph by actually building with them — not just reading about them.

## ✨ What it does

- 🧠 **Doubt-clearing (RAG)** — Ask "why," "how," or "when" questions about your own uploaded notes/textbook and get answers grounded in *your* material, with source citations.
- 📝 **Quiz generation (Agent)** — Ask to be quizzed on a topic and get 10 exam-style practice questions generated from your actual notes. No topic given? It defaults to your weakest topic automatically, or tells you honestly if it has no history yet.
- 📈 **Adaptive difficulty** — The agent tracks what you get wrong per topic and drops difficulty on topics you're struggling with.
- 🎯 **Manual weak-topic tagging** — Tell it directly "I'm not strong in X" and it'll prioritize that topic in future quizzes, without needing a quiz failure first.
- 📋 **Weak-topics lookup** — Ask "what are my weak topics?" and get a straight answer pulled from your actual history, not a guess.
- 👥 **Multi-student support** — Score history is tracked per student ID, so more than one person can use the same instance without their progress mixing.

## 🛠️ Tech stack

- [LangChain](https://www.langchain.com/) + [LangGraph](https://www.langchain.com/langgraph) — orchestration and agent logic
- [Chroma](https://www.trychroma.com/) — vector database for retrieval
- [Ollama](https://ollama.com) — running local open-source LLMs (Llama 3.2)
- FastAPI — API layer *(in progress)*
- React — frontend *(in progress)*

## 🚦 Status

| Piece | Status |
|---|---|
| Ingestion + retrieval (RAG) | ✅ working |
| LangGraph state machine (5 intents, 9 nodes) | ✅ working |
| Agent tools (quiz, scoring, weak-topic tracking) | ✅ working |
| Multi-student support | ✅ working |
| FastAPI endpoints | 🟡 in progress |
| React frontend | ⚪ not started |

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

A single LangGraph classifies intent, then routes to one of five branches:
- **Doubt** → retrieve → answer, with source citation
- **Quiz request** → check history → (retrieve → generate) or a clear "no history yet" message if there's nothing to go on
- **Submit answer** → log result against the explicit topic, or the last quiz topic if none was restated
- **Mark weak** → manually flag a topic as needing more practice
- **List weak topics** → read back current weak-topic history

A keyword fast-path handles the highest-value read-only intent (weak-topic lookup) directly, without an LLM call, since small local models showed some run-to-run classification instability on ambiguous phrasing.

## ⚠️ Known limitations (Day 1 scope)

- Intent classification via a 3B local model has some inherent instability on ambiguous or rephrased requests — one fast-path exists for the highest-value case, but not every phrasing is covered.
- No error handling yet if Ollama isn't running — will raise a raw exception (Day 2 fixes this at the API layer).
- Quiz generation quality depends on how well the underlying notes are chunked; sparse or poorly structured notes will produce weaker questions.
- Manually-tagged weak topics aren't validated against the actual notes corpus — you can tag a topic that doesn't exist in your material.
- Score history is a flat JSON file — fine for a handful of students, not built for real concurrency.
- State (like "last quiz topic") resets between separate runs of the CLI — no persistent session memory yet.

## 📄 License

MIT — see [LICENSE](./LICENSE).