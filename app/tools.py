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
def mark_topic_weak(student_id: str, topic: str) -> str:
    """Manually flag a topic as one the student wants more practice on,
    without needing a quiz failure first."""
    scores = _load_scores()
    student = scores.setdefault(student_id, {})
    stats = student.setdefault(topic, {"attempts": 1, "correct": 0})
    # only downgrade if not already tracked as weak, don't erase real history
    if stats.get("attempts", 0) == 0:
        stats["attempts"] = 1
        stats["correct"] = 0
    _save_scores(scores)
    return f"Got it - I'll prioritize {topic} in future quizzes."


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


@tool
def get_sample_topics(n: int = 3) -> list[str]:
    """Return a few topic-like phrases from the indexed notes, for
    use as example prompts. Pulled from document headings if available."""
    import re
    from app.config import NOTES_DIR
    import glob

    headings = []
    for path in glob.glob(f"{NOTES_DIR}/**/*.md", recursive=True):
        with open(path, "r", errors="ignore") as f:
            text = f.read()
        headings.extend(re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE))

    # crude fallback if no markdown headings exist (e.g. pdf/docx only)
    if not headings:
        return ["your notes", "a key concept", "a recent chapter"]

    import random
    random.shuffle(headings)
    return headings[:n]