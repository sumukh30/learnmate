"""
Builds the LearnMate LangGraph: one entry node that classifies intent,
then three branches — answer a doubt (RAG), generate a quiz (agent +
history), or log a submitted quiz answer.

Run the CLI test loop directly:
    python -m app.graph
"""
import json
from typing import TypedDict, Optional

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from app.config import LLM_MODEL, DEFAULT_STUDENT_ID
from app.retriever import retrieve
from app.tools import generate_quiz, log_quiz_result, get_weak_topics

_llm = ChatOllama(model=LLM_MODEL, temperature=0)


class State(TypedDict):
    query: str
    student_id: str
    intent: str
    topic: Optional[str]
    difficulty: Optional[str]
    is_correct: Optional[bool]
    retrieved_docs: list[dict]
    weak_topics: list[str]
    response: str


# ---------- Nodes ----------

def classify_intent(state: State) -> State:
    prompt = f"""Classify the user's request and extract fields as JSON only,
no other text. Fields:
- intent: one of "doubt", "quiz_request", "submit_answer"
- topic: the subject/topic mentioned, or null if none
- difficulty: "easy", "medium", or "hard" if mentioned, else null
- is_correct: true/false if the user is reporting whether their quiz
  answer was correct, else null

User request: "{state['query']}"

JSON:"""
    raw = _llm.invoke(prompt).content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"intent": "doubt", "topic": None, "difficulty": None, "is_correct": None}

    state["intent"] = parsed.get("intent", "doubt")
    state["topic"] = parsed.get("topic")
    state["difficulty"] = parsed.get("difficulty") or "medium"
    state["is_correct"] = parsed.get("is_correct")
    return state


def retrieve_context(state: State) -> State:
    topic = state.get("topic")
    docs = retrieve(state["query"], k=5, topic=topic)
    state["retrieved_docs"] = docs
    return state


def answer_doubt(state: State) -> State:
    context = "\n\n".join(d["text"] for d in state["retrieved_docs"])
    sources = ", ".join(sorted({d["source"] for d in state["retrieved_docs"]}))
    prompt = f"""Answer the student's question using ONLY the context
below. If the context doesn't contain the answer, say so honestly
instead of guessing. Keep the answer clear and exam-relevant.

Context:
{context}

Question: {state['query']}

Answer:"""
    answer = _llm.invoke(prompt).content
    state["response"] = f"{answer}\n\n(source: {sources})"
    return state


def check_history(state: State) -> State:
    weak = get_weak_topics.invoke({"student_id": state["student_id"]})
    state["weak_topics"] = weak
    if not state.get("topic") and weak:
        state["topic"] = weak[0]
    return state


def generate_quiz_node(state: State) -> State:
    context = "\n\n".join(d["text"] for d in state["retrieved_docs"])
    topic = state.get("topic") or "the retrieved material"

    difficulty = state["difficulty"]
    if topic in state.get("weak_topics", []) and difficulty == "medium":
        difficulty = "easy"

    quiz = generate_quiz.invoke({
        "topic": topic,
        "context": context,
        "difficulty": difficulty,
        "num_questions": 10,
    })
    note = ""
    if state.get("weak_topics"):
        note = f"\n\n(note: you've been weak on: {', '.join(state['weak_topics'])})"
    state["response"] = quiz + note
    return state


def log_result(state: State) -> State:
    topic = state.get("topic") or "general"
    correct = bool(state.get("is_correct"))
    result = log_quiz_result.invoke({
        "student_id": state["student_id"],
        "topic": topic,
        "correct": correct,
    })
    state["response"] = result
    return state


# ---------- Routing ----------

def route_intent(state: State) -> str:
    return {
        "doubt": "retrieve_for_doubt",
        "quiz_request": "check_history",
        "submit_answer": "log_result",
    }.get(state["intent"], "retrieve_for_doubt")


# ---------- Build graph ----------

def build_graph():
    graph = StateGraph(State)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_for_doubt", retrieve_context)
    graph.add_node("answer_doubt", answer_doubt)
    graph.add_node("check_history", check_history)
    graph.add_node("retrieve_for_quiz", retrieve_context)
    graph.add_node("generate_quiz", generate_quiz_node)
    graph.add_node("log_result", log_result)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges("classify_intent", route_intent, {
        "retrieve_for_doubt": "retrieve_for_doubt",
        "check_history": "check_history",
        "log_result": "log_result",
    })

    graph.add_edge("retrieve_for_doubt", "answer_doubt")
    graph.add_edge("answer_doubt", END)

    graph.add_edge("check_history", "retrieve_for_quiz")
    graph.add_edge("retrieve_for_quiz", "generate_quiz")
    graph.add_edge("generate_quiz", END)

    graph.add_edge("log_result", END)

    return graph.compile()


_app = None


def run(query: str, student_id: str = DEFAULT_STUDENT_ID) -> str:
    global _app
    if _app is None:
        _app = build_graph()
    initial_state: State = {
        "query": query,
        "student_id": student_id,
        "intent": "",
        "topic": None,
        "difficulty": None,
        "is_correct": None,
        "retrieved_docs": [],
        "weak_topics": [],
        "response": "",
    }
    final_state = _app.invoke(initial_state)
    return final_state["response"]


if __name__ == "__main__":
    print("LearnMate CLI — ask a doubt, request a quiz, or report an answer.")
    student_id = input("Enter your student ID (or press enter for default): ").strip()
    if not student_id:
        student_id = DEFAULT_STUDENT_ID
    print(f"\nLogged in as: {student_id}")
    print('Examples:')
    print('  "what is overfitting in machine learning?"')
    print('  "quiz me on overfitting, medium difficulty"')
    print('  "I got the overfitting question wrong"')
    print("(type 'exit' to quit)\n")

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        print("\n" + run(user_input, student_id=student_id) + "\n")