# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — FastAPI Application
# ──────────────────────────────────────────────────────────────
#
# Endpoints:
#   GET  /health             — liveness check
#   GET  /api/graph          — load lifetime graph (+ decay + session reset)
#   GET  /api/next-question  — generate the first question for a session
#   POST /api/evaluate       — full 8-step agentic cycle per interaction
# ──────────────────────────────────────────────────────────────

import logging
import os
import re

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import GRAPH_STORE_DIR, GROQ_MODEL
from models import (
    EvaluateRequest,
    EvaluateResponse,
    FirstQuestionResponse,
    GraphResponse,
    NodeFrontend,
    LinkFrontend,
    GraphState,
)
from memory.graph_store import GraphStore
from agents.graph_engine import GraphEngine
from agents.planner import plan_first_question
from agents.tutor import generate_question
from services.evaluation_pipeline import run_evaluation_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)


# ── App ───────────────────────────────────────────────────────

# CORS: read allowed origins from env for production hardening
_CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

app = FastAPI(
    title="Nanonautics ALS Backend",
    description="Agentic Learning System — Personalized Socratic tutor for competitive programming",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

store = GraphStore(GRAPH_STORE_DIR)
engine = GraphEngine()


# ── Startup validation ────────────────────────────────────────

@app.on_event("startup")
async def startup_checks():
    """Validate critical environment variables at startup so failures are loud."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        log.error(
            "GROQ_API_KEY is not set! "
            "Copy als_backend/.env.example → als_backend/.env and add your key. "
            "LLM calls will fail until this is fixed."
        )
    else:
        log.info(f"GROQ_API_KEY present (model: {GROQ_MODEL})")
    log.info(f"Graph store: {GRAPH_STORE_DIR}")
    log.info(f"CORS origins: {_CORS_ORIGINS}")


# ── Helpers ───────────────────────────────────────────────────

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_student_id(student_id: str) -> str:
    """Sanitize student_id: allow only alphanumerics, hyphens, underscores (max 64 chars)."""
    if not student_id or not _SAFE_ID.match(student_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid student_id. Use only letters, numbers, hyphens, and underscores (max 64 chars).",
        )
    return student_id


def graph_to_frontend(graph: GraphState) -> GraphResponse:
    """Convert internal graph (0.0–1.0) to frontend scale (0–100).
    Only return unlocked nodes and links between unlocked nodes."""
    unlocked_ids = {n.id for n in graph.nodes if n.unlocked}

    nodes = [
        NodeFrontend(
            id=n.id,
            field=n.field,
            mastery=round(n.mastery * 100, 2),
            confidence=round(n.confidence * 100, 2),
            decay=n.decay,
            error_rate=round(n.error_rate, 4),
        )
        for n in graph.nodes
        if n.unlocked
    ]

    links = [
        LinkFrontend(
            source=l.source,
            target=l.target,
            strength=round(l.strength, 4),
        )
        for l in graph.links
        if l.source in unlocked_ids and l.target in unlocked_ids
    ]

    return GraphResponse(
        nodes=nodes,
        links=links,
        sessionGraph=list(graph.session_concept_ids),
    )


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness check for load balancers and monitoring tools."""
    return {"status": "ok", "model": GROQ_MODEL}


@app.get("/api/graph", response_model=GraphResponse)
async def get_graph(student_id: str = Query(...)):
    """Load the student's lifetime graph, apply decay, and reset session flags.
    Called once when the frontend mounts."""
    student_id = validate_student_id(student_id)
    try:
        graph = store.load(student_id)
        graph = store.reset_session(graph)
        graph = engine.apply_decay(graph)
        store.save(student_id, graph)
        return graph_to_frontend(graph)
    except Exception as e:
        log.exception(f"get_graph failed for student '{student_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to load student graph.")


@app.get("/api/next-question", response_model=FirstQuestionResponse)
async def get_first_question(student_id: str = Query(...)):
    """Generate the opening question for a learning session."""
    student_id = validate_student_id(student_id)
    try:
        graph = store.load(student_id)
        first_directive = plan_first_question(graph)
        question, q_type = await generate_question(first_directive, "", graph)
        return FirstQuestionResponse(
            nextQuestion=question,
            questionType=q_type,
            targetConcept=first_directive.target_concept,
        )
    except Exception as e:
        log.exception(f"get_first_question failed for student '{student_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to generate opening question.")


@app.post("/api/evaluate", response_model=EvaluateResponse)
async def evaluate_response(req: EvaluateRequest):
    """Full 8-step agentic cycle with session rhythm and personality."""
    validate_student_id(req.student_id)
    try:
        return await run_evaluation_cycle(req, store, engine)

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"evaluate_response failed for student '{req.student_id}': {e}")
        raise HTTPException(status_code=500, detail="Evaluation pipeline failed. Please try again.")
