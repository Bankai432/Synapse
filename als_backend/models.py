# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Pydantic Models (Request / Response / Internal)
# ──────────────────────────────────────────────────────────────

from enum import Enum
from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, field_validator


# ── Enums ──────────────────────────────────────────────────────

class TutorMode(str, Enum):
    SOCRATIC = "SOCRATIC"
    PROPOSE_DIRECT = "PROPOSE_DIRECT"
    DIRECT = "DIRECT"
    PROPOSE_REPAIR = "PROPOSE_REPAIR"
    REPAIR = "REPAIR"

class PedagogicalPhase(str, Enum):
    CONCRETE = "CONCRETE"
    ABSTRACT = "ABSTRACT"
    FORMAL = "FORMAL"

# ── Request Models ────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    question: str
    user_input: str
    user_confidence: int  # 0–100
    student_id: str
    user_image: Optional[str] = None # Base64 data URL
    user_audio: Optional[str] = None # Base64 data URL
    exploration_mode: Optional[Literal["Depth", "Float", "Drift", "Socratic"]] = "Socratic"
    personality_mode: Optional[Literal["Socratic", "Nerdy", "Strict", "Collaborative"]] = "Socratic"
    learner_profile: Optional[str] = "struggling" # e.g. "struggling", "confident", "methodical"


# ── NTK Interaction Record ───────────────────────────────────

class NTKInteraction(BaseModel):
    """A single student interaction recorded in NTK kernel space.
    
    Fields:
        concept_id:     which concept node this interaction touched
        features:       x_i = [correctness, confidence, reasoning_quality,
                                mastery_before, error_rate_before]  ∈ R^5
        target_mastery: y_i = post-update mastery (the target in function space)
        timestamp:      Unix timestamp of the interaction
    """
    concept_id: str
    features: list[float]     # x_i ∈ R^5
    target_mastery: float     # y_i ∈ [0, 1]
    timestamp: float


# ── Core Internal Models ─────────────────────────────────────

class NodeState(BaseModel):
    id: str
    mastery: float          # 0.0–1.0 internally
    confidence: float       # 0.0–1.0 internally
    decay: float            # last decay factor applied (1.0 = no decay, 0.0 = fully decayed)
    error_rate: float       # 0.0–1.0 (clamped by engine)
    last_seen_ts: float
    error_patterns: list[str]
    tier: int
    field: str = "General"
    unlocked: bool
    session_activated: bool
    phase: PedagogicalPhase = PedagogicalPhase.CONCRETE


class LinkState(BaseModel):
    source: str
    target: str
    strength: float         # 0.0–1.0
    type: Literal["prerequisite", "co_activation"]
    co_activation_count: int


class SessionState(BaseModel):
    dept_on_node: int = 0
    last_3_nodes: list[str] = []
    momentum: Literal["deepening", "drifting", "bridging"] = "deepening"
    turns_since_connection_attempt: int = 0
    exploration_mode: Literal["Depth", "Float", "Drift", "Socratic"] = "Socratic"
    personality_mode: Literal["Socratic", "Nerdy", "Strict", "Collaborative"] = "Socratic"
    learner_profile: Optional[str] = "struggling"
    history: list[dict[str, str]] = []  # last 2-3 exchanges
    
    # ── Pedagogical Overhaul Fields ──
    current_mode: TutorMode = TutorMode.SOCRATIC
    mode_lock_turns: int = 0
    pending_explanation_concept: Optional[str] = None
    consecutive_errors: int = 0

class GraphState(BaseModel):
    nodes: list[NodeState]
    links: list[LinkState]
    session_concept_ids: list[str]
    session_start_ts: float
    session_state: Optional[SessionState] = None
    ntk_history: list[NTKInteraction] = []  # per-student interaction history for NTK kernel


class EvaluatorOutput(BaseModel):
    concepts_used: list[str]
    correctness: float
    confidence: float
    reasoning_quality: float
    novel_connections: list[list[str]]
    error_patterns: list[str]
    gap: str
    confidenceMismatch: bool
    is_analogy: bool = False
    pedagogical_nudge: Optional[str] = None

    @field_validator("correctness", "confidence", "reasoning_quality", mode="before")
    @classmethod
    def clamp_float(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


# ── Response Models (Frontend Contract) ──────────────────────

class ConceptUpdateDelta(BaseModel):
    id: str
    masteryDelta: Optional[float] = None
    confidenceDelta: Optional[float] = None
    decayDelta: Optional[float] = None
    errorDelta: Optional[float] = None


class NodeFrontend(BaseModel):
    id: str
    field: str = "General"
    mastery: float          # 0–100 scale for frontend
    confidence: float       # 0–100 scale for frontend
    decay: float            # last decay factor (1.0 = no decay)
    error_rate: float       # 0.0–1.0


class LinkFrontend(BaseModel):
    source: str
    target: str
    strength: float         # 0.0–1.0


class EvaluateResponse(BaseModel):
    gap: str
    confidenceMismatch: bool
    nextQuestion: str
    questionType: str
    transcription: Optional[str] = None
    conceptUpdates: list[ConceptUpdateDelta]
    newNodes: list[NodeFrontend]
    newLinks: list[LinkFrontend]


class GraphResponse(BaseModel):
    nodes: list[NodeFrontend]
    links: list[LinkFrontend]
    sessionGraph: list[str]


class FirstQuestionResponse(BaseModel):
    nextQuestion: str
    questionType: str
    targetConcept: str
