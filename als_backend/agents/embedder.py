# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Input Embedder (Phase 1: Socratic Features)
# ──────────────────────────────────────────────────────────────
#
# Builds the feature vector x_i ∈ R^5 for a single student interaction.
# Per the NTK spec: x_i = concat(e_text, e_audio, e_video, s_i)
#
# Phase 1 uses only Socratic features s_i — the scalar scores already
# produced by the Evaluator and GraphEngine. No external embedding
# model is required. Multimodal embeddings will be added in Phase 2.
#
# Feature vector layout:
#   x_i[0] = correctness          (LLM-evaluated, 0.0–1.0)
#   x_i[1] = inferred confidence  (LLM-evaluated, 0.0–1.0)
#   x_i[2] = reasoning_quality    (LLM-evaluated, 0.0–1.0)
#   x_i[3] = node.mastery         (pre-update, 0.0–1.0)
#   x_i[4] = node.error_rate      (pre-update, 0.0–1.0)
# ──────────────────────────────────────────────────────────────

from models import EvaluatorOutput, NodeState


def build_feature_vector(eval_output: EvaluatorOutput, node: NodeState) -> list[float]:
    """Build x_i ∈ R^5 for an interaction.

    Must be called BEFORE the node is updated by the GraphEngine so that
    node.mastery and node.error_rate reflect the pre-interaction state.

    Returns a plain list[float] for JSON-serialisability (stored in NTKInteraction).
    """
    return [
        float(eval_output.correctness),
        float(eval_output.confidence),
        float(eval_output.reasoning_quality),
        float(node.mastery),
        float(node.error_rate),
    ]
