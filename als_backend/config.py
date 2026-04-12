# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Hyperparameters & Constants
# ──────────────────────────────────────────────────────────────
#
# All time-dependent thresholds are in SECONDS.
# Real-world tuning targets are documented inline.
# ──────────────────────────────────────────────────────────────

# Graph Engine learning rates
ETA_1   = 0.08    # node mastery learning rate (reduced from 0.10)
ETA_2   = 0.05    # error accumulation rate  → clamped to [0, 1] in engine
ETA_3   = 0.06    # connection-making mastery bonus (reduced from 0.15)
ALPHA   = 0.70    # confidence blend: self-reported vs measured
ETA_W   = 0.08    # Hebbian edge learning rate
LAMBDA_ = 0.0000011  # decay constant per second
                     # → ~91% retention after 1 day
                     # → ~50% retention after 7 days
                     # → ~5%  retention after 30 days
                     # Formula: mastery × exp(−λ × Δt_seconds)

# Planner thresholds
MISCONCEPTION_CONFIDENCE_THRESHOLD = 0.65
MISCONCEPTION_CORRECTNESS_THRESHOLD = 0.45
SPACED_REPETITION_DECAY_THRESHOLD = 259200  # 3 days in seconds (72 × 3600)
REINFORCE_MASTERY_THRESHOLD = 0.35
CONNECTION_MASTERY_THRESHOLD = 0.50
CONNECTION_STRENGTH_THRESHOLD = 0.30
NOVEL_MASTERY_THRESHOLD = 0.60

# Unlock prerequisites
UNLOCK_EDGE_STRENGTH_MIN = 0.25
UNLOCK_MASTERY_MIN = 0.40

# New edge initialization
NEW_EDGE_INIT_STRENGTH = 0.05

# Pedagogical Overhaul Constants
GROUNDING_LOOP_LIMIT = 2
HEDGING_MASTERY_CAP = 0.05
MATURITY_REASONING_THRESHOLD = 0.4
MASTERY_MATURITY_GATE = 0.85
REASONING_STUNTING_THRESHOLD = 0.5
REASONING_STUNTING_FACTOR = 0.5

# LLM (Groq)
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_VISION_MODEL = "llama-4-scout-17b-16e-instruct"
GROQ_WHISPER_MODEL = "whisper-large-v3"
EVALUATOR_MAX_TOKENS = 600   # bumped from 512 — complex schema needs headroom
TUTOR_MAX_TOKENS = 350       # bumped from 256 — 3-sentence questions can be long
GROQ_MAX_RETRIES = 3         # retry attempts on transient API errors
GROQ_RETRY_BASE_DELAY = 1.0  # seconds — exponential back-off base

# Storage
GRAPH_STORE_DIR = "./student_graphs"

# ── NTK Engine (Phase 1 — Linearized Cosine Kernel) ──────────
NTK_MIN_INTERACTIONS  = 3     # interactions per concept before NTK predictions activate (reduced from 5)
NTK_WINDOW_SIZE       = 100   # max interactions retained per concept (sliding window)
NTK_REG_LAMBDA        = 1e-4  # Tikhonov regularisation: K + λI for stable inversion
NTK_BLEND             = 0.5   # weight of NTK prediction vs rule-based update
                               # 0.0 = pure rules, 1.0 = pure NTK
NTK_UNCERTAINTY_THRESHOLD = 0.15  # variance above which planner considers uncertainty-driven exploration
NTK_FEATURE_DIM       = 5     # dimensionality of x_i = [correctness, confidence, reasoning_quality, mastery, error_rate]
