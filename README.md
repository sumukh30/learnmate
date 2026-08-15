# 📚 LearnMate

**Your notes, made queryable. Your gaps, made visible.**

LearnMate is an adaptive study copilot — ask doubts on your own notes and textbooks, get quizzed on what you've learned, and let it quietly track what you're actually struggling with so future quizzes focus there instead of wherever you happen to click.

## 🎯 Why this was made?

Studying for an exam or interview usually means two disconnected habits: rereading notes when something's unclear, and separately trying to guess what kind of questions might come up. LearnMate merges both into one loop — the same material you're confused about is the same material it quizzes you on, and the same quiz results decide what it pushes you toward next.

## ✨ What it does?

- 🧠 **Ask a doubt** — "why does X happen," "how does Y work" — answered strictly from your own notes, with the source file cited, not from general model knowledge.
- 📝 **Take a quiz** — 10 exam-style questions generated from your material. No topic in mind? It defaults to your weakest area automatically, or tells you plainly if there's no history yet.
- 📈 **Adaptive difficulty** — quizzes get easier on topics you're struggling with, without you having to ask.
- 🎯 **Flag a weak spot manually** — "I'm not strong in backpropagation" and it's prioritized in future quizzes, validated against your actual notes first so it can't silently track a topic that doesn't exist.
- 📋 **Ask what you're weak on** — a straight, honest answer pulled from real history, not a guess.
- 👥 **Multi-student, session-persistent** — separate progress per student ID, and it remembers context (like "what quiz did I just take") even across restarts.

## 🧩 How it works?

A **LangGraph** state machine sits at the center. Every message is classified into one of five intents — doubt, quiz request, submit answer, mark weak, list weak topics — and routed to a different combination of retrieval and tool calls:

- **Doubt** → retrieve relevant chunks from a vector store → answer grounded strictly in that context.
- **Quiz** → check weak-topic history → retrieve chunks on the target topic → generate questions at the right difficulty.
- **Submit answer** → log correctness against the explicit or last-known topic, updating per-student accuracy.
- **Mark weak / list weak topics** → read or write the student's tracked history directly.

Two of the most unambiguous, highest-traffic intents are handled by a fast keyword check _before_ any LLM call — a 3B local model showed real run-to-run classification variance on certain phrasings, so the fast-path removes the LLM from the decision entirely where a deterministic rule is more reliable. Everything else still goes through the LLM classifier.

## 🛠️ Tech stack

| Layer               | Tool                              |
| ------------------- | --------------------------------- |
| Agent orchestration | LangChain + LangGraph             |
| Retrieval           | Chroma (vector store)             |
| LLM + embeddings    | Ollama, running Llama 3.2 locally |
| API                 | FastAPI                           |
| Frontend            | React (Vite)                      |

Entirely open-source, entirely local — no API keys, no per-request cost, no data leaving your machine.

## 🚀 Setup

```bash
# 1. Install Ollama and pull the models
ollama pull llama3.2
ollama pull nomic-embed-text

# 2. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.ingest        # index your notes
uvicorn app.main:app --reload

# 3. Frontend (new terminal tab)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, drop your own notes/textbooks (`.md`, `.txt`, `.pdf`, `.docx`) into `data/sample_notes/`, re-run `python -m app.ingest`, and it's studying your material.

## ⚠️ Known limitations

Being upfront about these matters more than pretending they don't exist:

- **Intent classification isn't perfect.** A 3B local model doing few-shot classification will misread some phrasings it hasn't seen close variants of. Two fast-paths cover the highest-value cases; the rest rely on the LLM and can occasionally misfire.
- **Self-reported grading.** "I got it wrong" is trusted, not verified — there's no automatic answer-checking against the generated correct answer.
- **Weak-topic validation is a keyword match**, not true semantic matching — a topic phrased differently than your notes may be rejected even if the concept exists.
- **Flat-file storage.** Score and session history are JSON files — fine for personal or small-group use, not built for real concurrency.
- **Local only, for now.** Runs on your machine via Ollama; not yet deployed to the cloud.

## 📄 License

MIT — see [LICENSE](./LICENSE).
