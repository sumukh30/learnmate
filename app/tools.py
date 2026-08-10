"""
LangChain @tool-decorated functions. These are the "actions" available
to the agent side of the graph — generating a quiz, logging a result,
and reading back a student's weak topics from history.
"""
import json
import os

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from app.config import SCORES_FILE, LLM_MODEL

_llm = ChatOllama(model=LLM_MODEL, temperature=0.4)


def _load_scores() -> dict:
    if not os.path.exists(SCORES_FILE):
        return {}
    with open(SCORES_FILE, "r") as f:
        return json.load(f)


def _save_scores(scores: dict) -> None:
    os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)


@tool
def get_weak_topics(student_id: str) -> list[str]:
    """Return topics where the student's past accuracy is below 70%,
    ordered worst-first. Empty list if no history exists yet."""
    scores = _load_scores().get(student_id, {})
    weak = []
    for topic, stats in scores.items():
        attempts = stats.get("attempts", 0)
        correct = stats.get("correct", 0)
        if attempts > 0 and (correct / attempts) < 0.7:
            weak.append((topic, correct / attempts))
    weak.sort(key=lambda pair: pair[1])
    return [topic for topic, _ in weak]


@tool
def log_quiz_result(student_id: str, topic: str, correct: bool) -> str:
    """Record whether the student answered a quiz question on `topic`
    correctly. Updates running accuracy for that topic."""
    scores = _load_scores()
    student = scores.setdefault(student_id, {})
    stats = student.setdefault(topic, {"attempts": 0, "correct": 0})
    stats["attempts"] += 1
    if correct:
        stats["correct"] += 1
    _save_scores(scores)
    accuracy = stats["correct"] / stats["attempts"]
    return f"Logged. {topic} accuracy is now {accuracy:.0%} over {stats['attempts']} attempt(s)."


@tool
def generate_quiz(topic: str, context: str, difficulty: str = "medium", num_questions: int = 3) -> str:
    """Generate `num_questions` quiz questions about `topic`, grounded
    in `context` (retrieved notes text), at the given difficulty."""
    prompt = f"""You are a study quiz generator. Using ONLY the context
below, write {num_questions} exam-style questions about "{topic}" at
{difficulty} difficulty. Mix question types (why/how/when, not just
what). After each question, add the correct answer on the next line
prefixed with "Answer:".

Context:
{context}

Format each question as:
Q1: <question>
Answer: <answer>
"""
    response = _llm.invoke(prompt)
    return response.content