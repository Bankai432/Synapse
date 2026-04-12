# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Tutor Agent (LLM Call 2)
# ──────────────────────────────────────────────────────────────
#
# Receives a structured directive from the Planner and generates
# one Socratic question. Does NOT decide what to ask — only how
# to phrase it.
# Features:
#   - Module-level singleton client (one connection pool)
#   - Retry with exponential back-off on transient errors
#   - Safe fallback question on total failure
# ──────────────────────────────────────────────────────────────

import asyncio
import json
import logging
import os

from groq import AsyncGroq, APIError, APIConnectionError, RateLimitError

from config import GROQ_MODEL, TUTOR_MAX_TOKENS, GROQ_MAX_RETRIES, GROQ_RETRY_BASE_DELAY
from models import GraphState
from agents.planner import PlannerDirective

log = logging.getLogger(__name__)


# ── Singleton client ──────────────────────────────────────────

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    """Return the module-level Groq client, initializing it once."""
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Copy als_backend/.env.example to als_backend/.env and add your key."
            )
        _client = AsyncGroq(api_key=api_key)
    return _client


# ── Safe fallback ─────────────────────────────────────────────

_FALLBACK_QUESTION = "Describe the time and space complexity of the concept you just explained. What are its worst-case guarantees?"
_FALLBACK_TYPE = "application"


# ── System Prompt ─────────────────────────────────────────────

TUTOR_SYSTEM_PROMPT = """\
You are an expert pedagogical tutor for STEAM subjects. Your goal is to guide students to mastery through a flexible blend of Socratic questioning and direct instruction.

Return ONLY valid JSON:
{
  "nextQuestion": "<the lesson or question — max 4 sentences>",
  "questionType": "<definition | application | edge_case | comparison | debug | lesson | proposal>"
}

Pedagogical Protocols (MANDATORY):

1. MODE-DRIVEN DYNAMICS:
   - SOCRATIC: (Default) Probe with questions. Never give the answer.
   - PROPOSE_DIRECT / PROPOSE_REPAIR: Proactively suggest a lesson. 
     *Phrase*: "It seems we've hit a roadblock with [Concept]. Would you like me to explain this directly, or keep trying on your own?"
   - DIRECT: (Explanation Mode) Give a clear, factual 1-2 sentence explanation before asking a simple 'concept_check' question.
   - REPAIR: (Hard Correction) 
     1. Quote the student's idea: "You said [X]..."
     2. Label it: "...actually, that's a common misconception."
     3. Replace it: "In physical reality, [Correct Model]..."

2. ANALOGY CONTROL:
   - If IS_ANALOGY is True, you MUST address it.
   - Validate the useful parts ("Your rubber band idea is good because it shows tension...")
   - Reject the invalid parts ("...but atoms aren't connected by actual strings").

3. PHYSICAL ANCHORING:
   - If PHASE is 'CONCRETE', your questions/explanations MUST include a tactile command.
   - Example: "Imagine pressing your thumb against the desk. Feel that resistance? That's the normal force."

4. SCAFFOLDING GATES:
   - Mastery < 0.35: Stick to 'definition' or 'lesson'.
   - Mastery > 0.7: Use 'comparison' or 'edge_case'.

Max length: 4 sentences. Be encouraging but precise.
"""


# ── Public API ────────────────────────────────────────────────

async def generate_question(
    directive: PlannerDirective,
    gap: str,
    graph: GraphState,
) -> tuple[str, str]:
    """Run LLM Call 2: generate the next Socratic response.
    
    Incorporates personality_mode and conversational history.
    """
    client = _get_client()
    session = graph.session_state
    
    personality = session.personality_mode if session else "Socratic"
    history = session.history if session else []
    
    node_map = {n.id: n for n in graph.nodes}
    target_node = node_map.get(directive.target_concept)

    if directive.action.value == "START_SESSION":
        return "Welcome. To calibrate your learning trajectory across Science, Technology, Engineering, Arts, and Mathematics, what specific field or concept would you like to explore first?", "calibration"

    user_message = f"""PERSONALITY MODE: {personality}
PEDAGOGICAL MODE: {session.current_mode.value if session else "SOCRATIC"}
CONVERSATION HISTORY: {json.dumps(history)}

PLANNER DIRECTIVE: {directive.action.value}
TARGET CONCEPT: {directive.target_concept}
PEDAGOGICAL PHASE: {target_node.phase.value if target_node else "CONCRETE"}
CURRENT MASTERY: {f"{target_node.mastery:.2f}" if target_node else "unknown"}
SEMANTIC GAP: {gap if gap else "N/A"}
IS_ANALOGY: {getattr(directive, 'is_analogy', False)}""" # We'll need to pass is_analogy through if possible or assume from gap

    raw = ""
    for attempt in range(GROQ_MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=TUTOR_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
            )
            raw = response.choices[0].message.content

            # Strip accidental markdown fences
            clean = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            data = json.loads(clean)
            if isinstance(data, str):
                # Handle double-encoded JSON if it happens
                data = json.loads(data)

            if not isinstance(data, dict):
                raise ValueError(f"LLM returned {type(data).__name__} instead of dict: {data!r}")

            question = data.get("nextQuestion", "").strip()
            q_type = data.get("questionType", _FALLBACK_TYPE).strip()

            if not question:
                raise ValueError("LLM returned empty nextQuestion field")

            # Validate question type
            valid_types = {"definition", "application", "edge_case", "comparison", "debug"}
            if q_type not in valid_types:
                q_type = _FALLBACK_TYPE

            return question, q_type

        except (RateLimitError, APIConnectionError) as e:
            delay = GROQ_RETRY_BASE_DELAY * (2 ** attempt)
            log.warning(f"Groq transient error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}), retrying in {delay:.1f}s: {e}")
            if attempt < GROQ_MAX_RETRIES - 1:
                await asyncio.sleep(delay)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            log.error(f"Tutor JSON parse error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}): {e}\nRaw: {raw!r}")
            if attempt < GROQ_MAX_RETRIES - 1:
                await asyncio.sleep(GROQ_RETRY_BASE_DELAY)

        except APIError as e:
            log.error(f"Groq API error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}): {e}")
            if attempt < GROQ_MAX_RETRIES - 1:
                await asyncio.sleep(GROQ_RETRY_BASE_DELAY)

        except Exception as e:
            log.exception(f"Unexpected tutor error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}): {e}")
            break

    log.error(f"Tutor exhausted all {GROQ_MAX_RETRIES} attempts. Returning fallback question.")
    return _FALLBACK_QUESTION, _FALLBACK_TYPE
