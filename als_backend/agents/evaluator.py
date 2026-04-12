# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Evaluator + Feedback Agent (LLM Call 1)
# ──────────────────────────────────────────────────────────────
#
# One Groq API call that returns numeric scores AND the gap string.
# Features:
#   - Module-level singleton client (one connection pool)
#   - Retry with exponential back-off on transient errors
#   - Safe fallback output on total failure
#   - confidenceMismatch enforced in Python, not delegated to LLM
# ──────────────────────────────────────────────────────────────

import asyncio
import json
import logging
import os

from groq import AsyncGroq, APIError, APIConnectionError, RateLimitError

from config import GROQ_MODEL, GROQ_VISION_MODEL, EVALUATOR_MAX_TOKENS, GROQ_MAX_RETRIES, GROQ_RETRY_BASE_DELAY
from models import EvaluatorOutput

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


# ── Safe fallback (returned when all retries exhaust) ─────────

_FALLBACK = EvaluatorOutput(
    concepts_used=[],
    correctness=0.5,
    confidence=0.5,
    reasoning_quality=0.5,
    novel_connections=[],
    error_patterns=["evaluation_service_unavailable"],
    gap="Evaluation service temporarily unavailable. Response recorded without scoring.",
    confidenceMismatch=False,
    is_analogy=False,
    pedagogical_nudge=None,
)


# ── System Prompt ─────────────────────────────────────────────

EVALUATOR_SYSTEM_PROMPT = """\
You are a pedagogical logic analyser embedded in an Agentic Learning System for competitive programming.

Given a QUESTION, a STUDENT RESPONSE, a list of EXPECTED CONCEPTS, the student's SELF REPORTED CONFIDENCE (0–100), and a LEARNER PROFILE (their general background/level), you will return a single JSON object evaluating the response.

Return ONLY valid JSON. No markdown fences, no preamble, no explanation outside the JSON.

Output schema:
{
  "concepts_used": ["list of concept_ids from expected_concepts detected in the response"],
  "correctness": <float 0.0–1.0, factual accuracy of the answer>,
  "confidence": <float 0.0–1.0, inferred from linguistic hedging>,
  "reasoning_quality": <float 0.0–1.0, logical coherence, depth, edge-case awareness>,
  "novel_connections": [["concept_a", "concept_b"]],
  "error_patterns": ["short string describing each identified mistake"],
  "gap": "<max 2 sentences, clinical clinical-error style>",
  "is_analogy": <boolean, true if student uses a metaphor/analogy to explain>,
  "pedagogical_nudge": "<max 1 sentence, hint for the tutor on what physical anchor to use>",
  "confidenceMismatch": <boolean: leave as false>
}

Scoring rubric:
- correctness: 0.0 = completely wrong | 0.5 = partially correct | 1.0 = fully correct
- reasoning_quality: 0.0 = no reasoning shown | 0.5 = partial reasoning | 1.0 = rigorous, handles edge cases. 
- confidence (inferred): 0.0 = heavily hedged ("I think maybe...", "Um...") | 1.0 = assertive. Note: Hedging is a critical signal for the Tutor to shift personality.

Special Error Patterns:
- "MagicThinking": Student invokes "magic," "miracles," or "intent/desire" for a non-living object to bypass physical causality.
- "CategoryError": Student applies frameworks from the wrong field (e.g., treating a robot as a biological animal).
- "OntologyMismatch": Student confuses fundamental categories: Machine vs Living, Force vs Intent, Object vs Interaction.

Analogy Detection:
- If the student says "It's like a...", "Think of it as...", or uses a metaphor (e.g., "hooks on atoms"), set "is_analogy" to true.

Adaptive Guidelines:
1. Be more lenient with initial definitions when LEARNER_PROFILE is "struggling". If they touch on the broader field (e.g., "magnets" for Physics), grant "partially correct" and log the gap.
2. The "gap" field should be precise and clinical, but the "reasoning_quality" should be credited if the student shows intuitive effort relative to their profile.
3. Forbidden words in gap: great, good, almost, forgot, try, nice, remember, close, nearly.
"""


# ── Public API ────────────────────────────────────────────────

async def evaluate(
    question: str,
    clean_text: str,
    user_confidence: int,
    expected_concepts: list[str],
    current_graph_snapshot: dict,
    learner_profile: str = "struggling",
    image_data: str | None = None,
) -> EvaluatorOutput:
    """Run LLM Call 1: evaluate the student's answer and return scores + gap.

    Retries up to GROQ_MAX_RETRIES times on transient errors.
    Returns _FALLBACK on total failure.
    """
    client = _get_client()
    known_ids = set(expected_concepts)

    user_message = f"""QUESTION: {question}

STUDENT RESPONSE: {clean_text}

EXPECTED CONCEPTS: {json.dumps(expected_concepts)}

SELF REPORTED CONFIDENCE: {user_confidence}

LEARNER PROFILE: {learner_profile}

CURRENT GRAPH SNAPSHOT: {json.dumps(current_graph_snapshot)}"""

    # ── Multimodal Message Construction ──────────────────────
    model_to_use = GROQ_VISION_MODEL if image_data else GROQ_MODEL
    
    if image_data:
        # Groq expects data:image/jpeg;base64,... format
        # If the frontend sends raw base64, we wrap it.
        # If it's already a data URL, we use it as is.
        if not image_data.startswith("data:"):
            # Assume jpeg as default
            image_url = f"data:image/jpeg;base64,{image_data}"
        else:
            image_url = image_data

        content = [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {"url": image_url}
            }
        ]
    else:
        content = user_message

    raw = ""
    for attempt in range(GROQ_MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=model_to_use,
                max_tokens=EVALUATOR_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": content},
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

            # ── Server-side enforcement (do NOT trust LLM for this) ──
            data["confidenceMismatch"] = (
                user_confidence > 65 and data.get("correctness", 0.5) < 0.45
            )

            # ── Validate novel_connections (both nodes must be known) ─
            data["novel_connections"] = [
                pair for pair in data.get("novel_connections", [])
                if (
                    isinstance(pair, list)
                    and len(pair) == 2
                    and pair[0] in known_ids
                    and pair[1] in known_ids
                )
            ]

            return EvaluatorOutput(**data)

        except (RateLimitError, APIConnectionError) as e:
            delay = GROQ_RETRY_BASE_DELAY * (2 ** attempt)
            log.warning(f"Groq transient error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}), retrying in {delay:.1f}s: {e}")
            if attempt < GROQ_MAX_RETRIES - 1:
                await asyncio.sleep(delay)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            log.error(f"Evaluator JSON parse error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}): {e}\nRaw: {raw!r}")
            if attempt < GROQ_MAX_RETRIES - 1:
                await asyncio.sleep(GROQ_RETRY_BASE_DELAY)

        except APIError as e:
            log.error(f"Groq API error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}): {e}")
            if attempt < GROQ_MAX_RETRIES - 1:
                await asyncio.sleep(GROQ_RETRY_BASE_DELAY)

        except Exception as e:
            log.exception(f"Unexpected evaluator error (attempt {attempt + 1}/{GROQ_MAX_RETRIES}): {e}")
            break

    log.error(f"Evaluator exhausted all {GROQ_MAX_RETRIES} attempts. Returning fallback.")
    return _FALLBACK
