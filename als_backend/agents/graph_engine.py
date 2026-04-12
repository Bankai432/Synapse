# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Graph Engine (pure deterministic math + NTK)
# ──────────────────────────────────────────────────────────────
#
# Implements the five core formulas:
#   Mastery update, Error update, Confidence blend,
#   Hebbian edge learning, Temporal decay.
#
# NTK Integration (Phase 1):
#   When a concept has ≥ NTK_MIN_INTERACTIONS recorded,
#   the mastery update blends the rule-based gain with the
#   NTK-predicted mastery via NTK_BLEND weighting.
# ──────────────────────────────────────────────────────────────

import logging
import time
import math

import numpy as np

from config import (
    ETA_1,
    ETA_2,
    ETA_3,
    ALPHA,
    ETA_W,
    LAMBDA_,
    NEW_EDGE_INIT_STRENGTH,
    UNLOCK_EDGE_STRENGTH_MIN,
    UNLOCK_MASTERY_MIN,
    NTK_BLEND,
    NTK_WINDOW_SIZE,
    HEDGING_MASTERY_CAP,
    MATURITY_REASONING_THRESHOLD,
    MASTERY_MATURITY_GATE,
    REASONING_STUNTING_THRESHOLD,
    REASONING_STUNTING_FACTOR,
)
from models import (
    GraphState,
    EvaluatorOutput,
    ConceptUpdateDelta,
    NodeFrontend,
    LinkFrontend,
    LinkState,
    NTKInteraction,
)
from seed.concept_graph import get_prerequisites
from agents.embedder import build_feature_vector
from agents.ntk_engine import NTKPredictor

log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────

def get_edge_strength(
    link_map: dict[tuple[str, str], LinkState],
    source: str,
    target: str,
) -> float:
    """Return edge strength between two nodes (either direction).
    Returns 0.0 if no edge exists."""
    edge = link_map.get((source, target)) or link_map.get((target, source))
    return edge.strength if edge else 0.0


# ── Engine ────────────────────────────────────────────────────

class GraphEngine:
    """Deterministic mathematical core of the ALS, augmented with NTK predictions."""

    def __init__(self):
        self._ntk = NTKPredictor()

    # ── Decay (runs once per session on load) ─────────────────

    def apply_decay(self, graph: GraphState) -> GraphState:
        """Apply temporal decay to all nodes not yet activated this session.

        Formula: m_i = m_i × exp(−λ × Δt_seconds)

        Also writes the decay factor to node.decay so the frontend
        can display how much a node has faded since last session.
        """
        now = time.time()
        for node in graph.nodes:
            if not node.session_activated:
                delta_t = now - node.last_seen_ts
                decay_factor = math.exp(-LAMBDA_ * delta_t)
                old_mastery = node.mastery
                node.mastery = max(0.0, min(1.0, node.mastery * decay_factor))
                # Write the actual decay factor experienced (1.0 = no decay)
                node.decay = round(decay_factor, 6)
        return graph

    # ── Main update (runs per interaction) ────────────────────

    def update(
        self,
        graph: GraphState,
        eval_output: EvaluatorOutput,
        user_confidence: int,
    ) -> tuple[GraphState, list[ConceptUpdateDelta], list[NodeFrontend], list[LinkFrontend], list[str]]:
        """Apply all graph mutations from a single student interaction.

        Returns:
            (updated_graph, concept_deltas, newly_unlocked_nodes, newly_created_links, unlock_reasons)
        """
        deltas: list[ConceptUpdateDelta] = []
        new_nodes: list[NodeFrontend] = []
        new_links: list[LinkFrontend] = []
        unlock_reasons: list[str] = []

        self_confidence_normalized = user_confidence / 100.0
        node_map: dict[str, object] = {n.id: n for n in graph.nodes}
        link_map: dict[tuple[str, str], LinkState] = {
            (l.source, l.target): l for l in graph.links
        }

        # ── 1. NODE UPDATES ───────────────────────────────────
        ntk_interactions_to_add: list[NTKInteraction] = []

        for concept_id in eval_output.concepts_used:
            if concept_id not in node_map:
                continue
            node = node_map[concept_id]
            old_mastery = node.mastery
            old_confidence = node.confidence
            old_error = node.error_rate

            # ── Build NTK feature vector BEFORE update ────────
            x_i = build_feature_vector(eval_output, node)
            x_np = np.array(x_i)

            # ── Rule-based mastery gain (original formula) ────
            mastery_gain = (ETA_1 * (eval_output.correctness * eval_output.reasoning_quality)) + \
                           (ETA_3 * len(eval_output.novel_connections) * eval_output.correctness)

            # ── SKEPTICISM: Cap or Scale gain ─────────────────
            # If magic/ontology error detected, never grant significant mastery
            grounding_errors = {"MagicThinking", "CategoryError", "OntologyMismatch"}
            if any(e in eval_output.error_patterns for e in grounding_errors):
                mastery_gain = min(mastery_gain, HEDGING_MASTERY_CAP)
                log.info(f"Skepticism active [{concept_id}]: capped gain due to grounding errors")

            # MATURITY CHECK: Gate full mastery behind reasoning quality
            if node.mastery > MASTERY_MATURITY_GATE and eval_output.reasoning_quality < MATURITY_REASONING_THRESHOLD:
                mastery_gain = 0.0
                log.info(f"Maturity locked [{concept_id}]: low reasoning quality at high mastery")

            # ── DIFFICULTY: Reasoning Stunting (unrelated answers) ─────
            # If answer is correct but reasoning is poor, stunt the gain
            if eval_output.correctness > 0.8 and eval_output.reasoning_quality < REASONING_STUNTING_THRESHOLD:
                mastery_gain *= REASONING_STUNTING_FACTOR
                log.info(f"Mastery Stunted [{concept_id}]: Correct answer with low reasoning quality.")

            # ── PROGRESSION: Diminishing Returns ─────────────────────
            # Mastery gain slows down as it gets higher (harder to reach 1.0)
            mastery_gain *= (1.0 - node.mastery)

            rule_mastery = min(1.0, node.mastery + mastery_gain)

            # ── NTK-guided mastery blend ──────────────────────
            ntk_result = self._ntk.run(concept_id, x_np, graph.ntk_history)
            if ntk_result.is_active:
                # Blend: mastery = (1 - β) × rule_mastery + β × ntk_predicted
                blended = (1.0 - NTK_BLEND) * rule_mastery + NTK_BLEND * ntk_result.predicted_mastery
                node.mastery = max(0.0, min(1.0, blended))
                log.info(
                    f"NTK active [{concept_id}]: rule={rule_mastery:.4f}, "
                    f"ntk={ntk_result.predicted_mastery:.4f}, "
                    f"blended={node.mastery:.4f}, unc={ntk_result.uncertainty:.4f}"
                )
            else:
                node.mastery = rule_mastery

            # Error: e_i = e_i + η₂ × (1 − correctness)  — clamped to [0, 1]
            node.error_rate += ETA_2 * (1.0 - eval_output.correctness)
            node.error_rate = max(0.0, min(1.0, node.error_rate))

            # Confidence: c_i = α × self_conf_norm + (1 − α) × correctness
            node.confidence = (
                ALPHA * self_confidence_normalized
                + (1 - ALPHA) * eval_output.correctness
            )
            node.confidence = max(0.0, min(1.0, node.confidence))

            # Error patterns (keep last 20 to prevent unbounded growth)
            node.error_patterns.extend(eval_output.error_patterns)
            node.error_patterns = node.error_patterns[-20:]

            # Session tracking
            node.last_seen_ts = time.time()
            node.session_activated = True
            node.decay = 1.0  # reset decay factor — node was just seen

            # ── Record NTK interaction (y_i = post-update mastery) ──
            ntk_interactions_to_add.append(
                NTKInteraction(
                    concept_id=concept_id,
                    features=x_i,
                    target_mastery=node.mastery,
                    timestamp=time.time(),
                )
            )

            # Delta for frontend (mastery/confidence on 0–100 scale)
            delta = ConceptUpdateDelta(
                id=concept_id,
                masteryDelta=round((node.mastery - old_mastery) * 100, 2),
                confidenceDelta=round((node.confidence - old_confidence) * 100, 2),
                errorDelta=round(node.error_rate - old_error, 4),
                decayDelta=0.0,
            )
            deltas.append(delta)

        # ── Persist NTK interactions (with sliding window) ────
        graph.ntk_history.extend(ntk_interactions_to_add)
        if len(graph.ntk_history) > NTK_WINDOW_SIZE * 10:  # global cap
            graph.ntk_history = graph.ntk_history[-(NTK_WINDOW_SIZE * 10):]

        # ── 2. HEBBIAN EDGE UPDATES ───────────────────────────
        activated = eval_output.concepts_used
        for i in range(len(activated)):
            for j in range(i + 1, len(activated)):
                a = activated[i]
                b = activated[j]
                # Only update edges between known nodes
                a_i = 1.0 if a in node_map else 0.0
                a_j = 1.0 if b in node_map else 0.0
                if a_i == 0.0 or a_j == 0.0:
                    continue
                hebbian_delta = ETA_W * a_i * a_j * eval_output.correctness

                key = (a, b)
                rev_key = (b, a)
                if key in link_map:
                    link_map[key].strength = min(1.0, link_map[key].strength + hebbian_delta)
                    link_map[key].co_activation_count += 1
                elif rev_key in link_map:
                    link_map[rev_key].strength = min(1.0, link_map[rev_key].strength + hebbian_delta)
                    link_map[rev_key].co_activation_count += 1

        # ── 3. NOVEL CONNECTION INITIALIZATION ────────────────
        for pair in eval_output.novel_connections:
            if len(pair) != 2:
                continue
            a, b = pair[0], pair[1]
            # Only create edges between nodes that actually exist in the graph
            if a not in node_map or b not in node_map:
                continue
            key = (a, b)
            rev_key = (b, a)
            if key not in link_map and rev_key not in link_map:
                new_link = LinkState(
                    source=a,
                    target=b,
                    strength=NEW_EDGE_INIT_STRENGTH,
                    type="co_activation",
                    co_activation_count=1,
                )
                graph.links.append(new_link)
                link_map[key] = new_link
                new_links.append(
                    LinkFrontend(source=a, target=b, strength=NEW_EDGE_INIT_STRENGTH)
                )

        # ── 4. UNLOCK CHECK ───────────────────────────────────
        for node in graph.nodes:
            if node.unlocked:
                continue
            prereqs = get_prerequisites(node.id)
            # BUGFIX: nodes with no known prerequisites must NOT auto-unlock
            if not prereqs:
                continue
            
            # GATE: Unlock only if at least one prerequisite was used in this interaction
            used_prereqs = [p for p in prereqs if p in eval_output.concepts_used]
            if not used_prereqs:
                continue

            all_met = all(
                p in node_map
                and node_map[p].mastery >= UNLOCK_MASTERY_MIN
                and get_edge_strength(link_map, p, node.id) >= UNLOCK_EDGE_STRENGTH_MIN
                for p in prereqs
            )
            if all_met:
                node.unlocked = True
                new_nodes.append(
                    NodeFrontend(
                        id=node.id,
                        field=node.field,
                        mastery=round(node.mastery * 100, 2),
                        confidence=round(node.confidence * 100, 2),
                        decay=node.decay,
                        error_rate=round(node.error_rate, 4),
                    )
                )
                prereqs_str = ", ".join(used_prereqs)
                unlock_reasons.append(f"Unlocked {node.id}: Mastery demonstrated in {prereqs_str}.")

        # ── 5. SESSION SUBGRAPH UPDATE ────────────────────────
        for concept_id in eval_output.concepts_used:
            if concept_id not in graph.session_concept_ids:
                graph.session_concept_ids.append(concept_id)

        return graph, deltas, new_nodes, new_links, unlock_reasons
