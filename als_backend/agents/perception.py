# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Perception Agent (deterministic)
# ──────────────────────────────────────────────────────────────
#
# Simple text normalisation. No LLM.
# ──────────────────────────────────────────────────────────────

import re


def perceive(raw_input: str) -> str:
    """Normalise student input text.

    - Strip leading/trailing whitespace
    - Collapse multiple spaces into a single space
    - Do NOT lowercase — evaluator needs original casing for concept detection
    """
    text = raw_input.strip()
    text = re.sub(r"\s+", " ", text)
    return text
