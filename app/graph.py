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
from app.tools import generate_quiz, log_quiz_result, get_weak_topics, mark_topic_weak

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
    last_quiz_topic: Optional[str]
    response: str


# ---------- Nodes ----------

def classify_intent(state: State) -> State:
    query_lower = state["query"].lower()

    # Fast-path: unambiguous read-only requests for weak topics don't
    # need an LLM call at all, and this sidesteps classifier flakiness
    # on a 3B model for a case that's cheap to detect directly.
    weak_topic_phrases = [
        "my weak topics", "weak topics", "struggling with", "struggling on",
        "what should i focus on", "what am i bad at", "weak areas",
    ]
    if any(phrase in query_lower for phrase in weak_topic_phrases) and "add" not in query_lower and "mark" not in query_lower:
        state["intent"] = "list_weak_topics"
        state["topic"] = None
        state["difficulty"] = "medium"
        state["is_correct"] = None
        return state
    prompt = f"""Classify the user's request and extract fields as JSON only,
    no other text. Fields:
    - intent: one of "doubt", "quiz_request", "submit_answer", "mark_weak", "list_weak_topics"
    - topic: the subject/topic mentioned, or null if none
    - difficulty: "easy", "medium", or "hard" if mentioned, else null
    - is_correct: true/false if the user is reporting whether their quiz
    answer was correct, else null

    Use "mark_weak" when the user explicitly states they personally find a
    specific topic difficult, confusing, or weak — including phrases like
    "I'm not strong in X", "I struggle with X", "I find X confusing", or
    "add X to my weak topics" — even without an explicit request to add it.
    Do NOT use "mark_weak" if the user is asking a question ABOUT their
    weak topics (e.g. "what are my weak topics?") — that is intent "doubt".

    Use "list_weak_topics" when the user is asking to see or be told what
    their weak topics are — including phrasings like "what are my weak
    topics?", "what am I struggling with?", "what should I focus on?",
    "what am I bad at?", or "show me my weak areas". This is different
    from "mark_weak", which is for the user declaring a NEW weak topic
    (e.g. "I'm not strong in X").

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
    prompt = f"""Answer the student's question using the context below as
your primary source. The context may use different wording than the
question — if a concept in the question is clearly discussed in the
context under a related term or explanation, use that to answer, even
if the exact keyword isn't repeated verbatim. Only say the context
doesn't cover it if it's genuinely unrelated, not just differently worded.
Keep the answer clear and exam-relevant.

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


def no_topic_response(state: State) -> State:
    state["response"] = "You have no quiz history yet — try asking to be quizzed on a specific topic first."
    return state


def mark_weak_node(state: State) -> State:
    topic = state.get("topic")
    if not topic:
        state["response"] = "Which topic would you like me to mark as weak? Please name it explicitly."
        return state
    result = mark_topic_weak.invoke({
        "student_id": state["student_id"],
        "topic": topic,
    })
    state["response"] = result
    return state


def list_weak_topics_node(state: State) -> State:
    weak = get_weak_topics.invoke({"student_id": state["student_id"]})
    if not weak:
        state["response"] = "You don't have any recorded weak topics yet — take a quiz first, or tell me a topic you're struggling with."
    else:
        state["response"] = f"Based on your quiz history, you're weakest on: {', '.join(weak)}."
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
    state["last_quiz_topic"] = topic
    return state


def log_result(state: State) -> State:
    topic = state.get("topic") or state.get("last_quiz_topic") or "general"
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
        "mark_weak": "mark_weak",
        "list_weak_topics": "list_weak_topics",
    }.get(state["intent"], "retrieve_for_doubt")


def route_after_history(state: State) -> str:
    if not state.get("topic"):
        return "no_topic_response"
    return "retrieve_for_quiz"

# ---------- Build graph ----------

def build_graph():
    graph = StateGraph(State)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_for_doubt", retrieve_context)
    graph.add_node("answer_doubt", answer_doubt)
    graph.add_node("check_history", check_history)
    graph.add_node("retrieve_for_quiz", retrieve_context)
    graph.add_node("generate_quiz", generate_quiz_node)
    graph.add_node("mark_weak", mark_weak_node)
    graph.add_node("no_topic_response", no_topic_response)
    graph.add_node("list_weak_topics", list_weak_topics_node)
    graph.add_node("log_result", log_result)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges("classify_intent", route_intent, {
        "retrieve_for_doubt": "retrieve_for_doubt",
        "check_history": "check_history",
        "log_result": "log_result",
        "mark_weak": "mark_weak",
        "list_weak_topics": "list_weak_topics",
    })

    graph.add_edge("retrieve_for_doubt", "answer_doubt")
    graph.add_edge("answer_doubt", END)

    graph.add_conditional_edges("check_history", route_after_history, {
    "retrieve_for_quiz": "retrieve_for_quiz",
    "no_topic_response": "no_topic_response",
    })
    graph.add_edge("retrieve_for_quiz", "generate_quiz")
    graph.add_edge("generate_quiz", END)

    graph.add_edge("mark_weak", END)
    graph.add_edge("no_topic_response", END)

    graph.add_edge("list_weak_topics", END)

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
        "last_quiz_topic": None,
        "response": "",
    }
    final_state = _app.invoke(initial_state)
    return final_state["response"]


if __name__ == "__main__":
    print("LearnMate — ask a doubt, request a quiz, or report an answer.")
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