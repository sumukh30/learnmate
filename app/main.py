"""
FastAPI wrapper around the LearnMate LangGraph. This is the HTTP
boundary — every endpoint here is a thin call into app.graph.run()
or app.ingest.build_index(). No LangGraph/RAG logic lives here.

Run with:
    uvicorn app.main:app --reload
"""
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.graph import run
from app.config import DEFAULT_STUDENT_ID

app = FastAPI(title="LearnMate API")

# Allows a React dev server (different port) to call this API from
# the browser. Restrict origins to something specific before any
# real deployment. "*" is fine for local development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    student_id: str = DEFAULT_STUDENT_ID


class AskResponse(BaseModel):
    response: str


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    """
    Single entry point for everything: doubts, quiz requests, answer
    submissions, weak-topic tagging, weak-topic lookups. The graph's
    own intent classification decides what happens — this endpoint
    doesn't need to know or care which branch runs.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty.")
    try:
        result = run(payload.query, student_id=payload.student_id)
        return AskResponse(response=result)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Can't reach the local model. Is Ollama running?")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Something went wrong: {str(e)}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/topics")
def topics():
    from app.tools import get_sample_topics
    return {"topics": get_sample_topics.invoke({"n": 3})}