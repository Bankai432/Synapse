# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Planner Agent (rule-based + NTK uncertainty)
# ──────────────────────────────────────────────────────────────
#
# Priority-ordered rule evaluation on graph state.
# NTK uncertainty drives exploration when the model
# has low confidence in a concept's predicted mastery.
# Returns exactly one PlannerDirective per call.
# ──────────────────────────────────────────────────────────────

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from config import (
    MISCONCEPTION_CONFIDENCE_THRESHOLD,
    MISCONCEPTION_CORRECTNESS_THRESHOLD,
    SPACED_REPETITION_DECAY_THRESHOLD,
    REINFORCE_MASTERY_THRESHOLD,
    CONNECTION_MASTERY_THRESHOLD,
    CONNECTION_STRENGTH_THRESHOLD,
    NOVEL_MASTERY_THRESHOLD,
    NTK_UNCERTAINTY_THRESHOLD,
)
from models import GraphState, EvaluatorOutput


# ── Types ─────────────────────────────────────────────────────

class PlannerAction(Enum):
    CHALLENGE_MISCONCEPTION = "CHALLENGE_MISCONCEPTION"
    UNCERTAINTY_REDUCE      = "UNCERTAINTY_REDUCE"
    SPACED_REPETITION       = "SPACED_REPETITION"
    REINFORCE               = "REINFORCE"
    BUILD_CONNECTION        = "BUILD_CONNECTION"
    NOVEL_PROBLEM           = "NOVEL_PROBLEM"
    START_SESSION           = "START_SESSION"
    
    # ── Overhaul Actions ──
    PROPOSE_DIRECT          = "PROPOSE_DIRECT"
    DIRECT                  = "DIRECT"
    PROPOSE_REPAIR          = "PROPOSE_REPAIR"
    REPAIR                  = "REPAIR"


@dataclass
class PlannerDirective:
    action: PlannerAction
    target_concept: str
    target_edge: Optional[tuple[str, str]] = None


# ── Main planner ──────────────────────────────────────────────

def plan(
    graph: GraphState,
    last_eval: EvaluatorOutput,
    user_confidence: int,
) -> PlannerDirective:
    """Evaluate priority rules against the current graph state and session rhythm.
    
    Returns exactly one PlannerDirective per call.
    Emits a ReasoningTrace to the backend logs for auditability.
    """
    import logging
    logger = logging.getLogger("planner")

    session = graph.session_state
    if not session:
        from models import SessionState
        session = SessionState()
        graph.session_state = session

    node_map = {n.id: n for n in graph.nodes}
    link_map = {(l.source, l.target): l for l in graph.links}
    unlocked_nodes = [n for n in graph.nodes if n.unlocked]
    activated_nodes = [n for n in unlocked_nodes if n.session_activated]
    
    trace = {
        "action": None,
        "target": None,
        "reason": None,
        "rhythm_influence": None,
        "exploration_mode": session.exploration_mode,
        "alternatives": []
    }

    # ── 1. RHYTHM & SESSION TRACKING ──────────────────────────
    session.turns_since_connection_attempt += 1
    
    # Update consecutive errors
    if last_eval.correctness < 0.4:
        session.consecutive_errors += 1
    else:
        session.consecutive_errors = 0

    # Decrement mode lock
    if session.mode_lock_turns > 0:
        session.mode_lock_turns -= 1

    from models import TutorMode, PedagogicalPhase

    # ── 2. CONSENT DETECTION ──────────────────────────────────
    user_said_yes = any(word in last_eval.gap.lower() or word in last_eval.error_patterns for word in ["yes", "explain", "help", "please"]) # Fallback check
    # Actually, we should check the clean_text, but we only have gap/correctness/etc in last_eval
    # Let's assume the evaluator might flag a "RequestHelp" error pattern or we check history
    
    # ── 3. MODE-BASED SELECTION ───────────────────────────────
    # If we are in a locked mode, stick to it
    if session.mode_lock_turns > 0:
        if session.current_mode == TutorMode.REPAIR:
            return PlannerDirective(PlannerAction.REPAIR, session.pending_explanation_concept or unlocked_nodes[0].id)
        if session.current_mode == TutorMode.DIRECT:
            return PlannerDirective(PlannerAction.DIRECT, session.pending_explanation_concept or unlocked_nodes[0].id)

    # Check for Consent to Proposals
    if session.current_mode == TutorMode.PROPOSE_DIRECT and last_eval.correctness > 0.0: # simplified "yes" detection
         session.current_mode = TutorMode.DIRECT
         session.mode_lock_turns = 1
         return PlannerDirective(PlannerAction.DIRECT, session.pending_explanation_concept)
    
    if session.current_mode == TutorMode.PROPOSE_REPAIR and last_eval.correctness > 0.0:
         session.current_mode = TutorMode.REPAIR
         session.mode_lock_turns = 1
         return PlannerDirective(PlannerAction.REPAIR, session.pending_explanation_concept)

    # ── 4. PRIORITY RULES ─────────────────────────────────────
    
    # ── PRIORITY 1: Ontological Grounding & Misconceptions ──────
    grounding_errors = {"MagicThinking", "CategoryError"}
    detected_grounding = [e for e in last_eval.error_patterns if e in grounding_errors]
    
    if detected_grounding:
        target = last_eval.concepts_used[0] if last_eval.concepts_used else session.last_3_nodes[-1] if session.last_3_nodes else unlocked_nodes[0].id
        session.current_mode = TutorMode.PROPOSE_REPAIR
        session.pending_explanation_concept = target
        return PlannerDirective(PlannerAction.PROPOSE_REPAIR, target)

    # ── PRIORITY 2: Straying Too Far / Direct Explanation ─────
    if session.consecutive_errors >= 2 or last_eval.correctness < 0.15:
        target = last_eval.concepts_used[0] if last_eval.concepts_used else session.last_3_nodes[-1] if session.last_3_nodes else unlocked_nodes[0].id
        session.current_mode = TutorMode.PROPOSE_DIRECT
        session.pending_explanation_concept = target
        return PlannerDirective(PlannerAction.PROPOSE_DIRECT, target)

    # ── PRIORITY 2: Forced Rhythm Pivot ───────────────────────
    if session.dept_on_node >= 3:
        trace["rhythm_influence"] = "depth_limit_reached (3 turns), forcing pivot"
        # Force a pivot to a new node or a bridging question
        # We'll skip down to other priorities and ensure we don't pick the same node
        avoid_node = session.last_3_nodes[-1] if session.last_3_nodes else None
    else:
        avoid_node = None

    # ── PRIORITY 3: Periodic Connection Force ─────────────────
    if session.turns_since_connection_attempt >= 5:
        # Find a mastered pair to bridge
        mastered = [n for n in unlocked_nodes if n.mastery >= CONNECTION_MASTERY_THRESHOLD]
        if len(mastered) >= 2:
            weakest_edge = None
            weakest_strength = 1.1
            for i in range(len(mastered)):
                for j in range(i + 1, len(mastered)):
                    a_id, b_id = mastered[i].id, mastered[j].id
                    edge = link_map.get((a_id, b_id)) or link_map.get((b_id, a_id))
                    if edge and edge.strength < weakest_strength:
                        weakest_strength = edge.strength
                        weakest_edge = (a_id, b_id)
            if weakest_edge:
                session.turns_since_connection_attempt = 0
                trace.update({"action": "BUILD_CONNECTION", "target": weakest_edge[0], "reason": "periodic_connection_force"})
                logger.info(f"Planner Reasoning: {trace}")
                return PlannerDirective(PlannerAction.BUILD_CONNECTION, weakest_edge[0], weakest_edge)

    # ── PRIORITY 4: Spaced repetition ─────────────────────────
    now = time.time()
    decaying = [
        n for n in unlocked_nodes
        if not n.session_activated
        and (now - n.last_seen_ts) > SPACED_REPETITION_DECAY_THRESHOLD
        and n.mastery < 0.70
        and n.id != avoid_node
    ]
    if decaying:
        target = max(decaying, key=lambda n: (now - n.last_seen_ts) * (1 - n.mastery))
        trace.update({"action": "SPACED_REPETITION", "target": target.id, "reason": "spaced_repetition"})
        logger.info(f"Planner Reasoning: {trace}")
        return PlannerDirective(PlannerAction.SPACED_REPETITION, target.id)

    # ── PRIORITY 4.5: NTK Uncertainty Exploration ─────────────
    # If the NTK model has high uncertainty about a concept's
    # mastery prediction, the planner proactively explores it.
    if graph.ntk_history:  # Only attempt if we have any NTK history
        import numpy as np
        from agents.ntk_engine import NTKPredictor

        _ntk = NTKPredictor()
        best_unc_node = None
        best_unc_val = -1.0

        for n in unlocked_nodes:
            if n.id == avoid_node:
                continue
            # Build a hypothetical probe vector for this concept
            probe_features = np.array([
                last_eval.correctness,
                last_eval.confidence,
                last_eval.reasoning_quality,
                n.mastery,
                n.error_rate,
            ])
            result = _ntk.run(n.id, probe_features, graph.ntk_history)
            if result.is_active and result.uncertainty > NTK_UNCERTAINTY_THRESHOLD:
                if result.uncertainty > best_unc_val:
                    best_unc_val = result.uncertainty
                    best_unc_node = n

        if best_unc_node:
            trace.update({
                "action": "UNCERTAINTY_REDUCE",
                "target": best_unc_node.id,
                "reason": f"ntk_uncertainty={best_unc_val:.4f}"
            })
            logger.info(f"Planner Reasoning: {trace}")
            return PlannerDirective(PlannerAction.UNCERTAINTY_REDUCE, best_unc_node.id)

    # ── PRIORITY 5: Reinforce / Advance (Mode-Dependent) ──────
    target_node = None
    action = PlannerAction.REINFORCE

    if session.exploration_mode == "Depth":
        # Strategy: Stay on weakest activated node until mastery threshold
        if activated_nodes:
            target_node = min(activated_nodes, key=lambda n: n.mastery)
            if target_node.mastery > 0.8: # If high mastery, move on
                 target_node = None
    
    elif session.exploration_mode == "Float":
        # Strategy: Current node + neighbors
        if activated_nodes:
            base = activated_nodes[-1]
            neighbors = [node_map[l.target] if l.source == base.id else node_map[l.source] 
                         for l in graph.links if (l.source == base.id or l.target == base.id)]
            neighbors = [n for n in neighbors if n.unlocked and n.id != avoid_node]
            if neighbors:
                 target_node = min(neighbors, key=lambda n: n.mastery)

    elif session.exploration_mode == "Drift":
        # Follow student's strongest connections
        if activated_nodes:
            base = activated_nodes[-1]
            candidates = [l for l in graph.links if (l.source == base.id or l.target == base.id)]
            if candidates:
                strongest_link = max(candidates, key=lambda l: l.strength)
                next_id = strongest_link.target if strongest_link.source == base.id else strongest_link.source
                target_node = node_map[next_id]
                if not target_node.unlocked: target_node = None

    # Default / Fallback
    if not target_node:
        if activated_nodes:
            target_node = min(activated_nodes, key=lambda n: n.mastery)
        else:
            target_node = min(unlocked_nodes, key=lambda n: n.mastery)

    # ── 5. KNOWLEDGE LADDERING (Phase Gating) ─────────────────
    # Ensure student passes through CONCRETE -> ABSTRACT -> FORMAL
    if target_node:
        if target_node.phase == PedagogicalPhase.CONCRETE and target_node.mastery > 0.6:
            target_node.phase = PedagogicalPhase.ABSTRACT
            logger.info(f"Phase Promotion: {target_node.id} -> ABSTRACT")
        elif target_node.phase == PedagogicalPhase.ABSTRACT and target_node.mastery > 0.85:
            target_node.phase = PedagogicalPhase.FORMAL
            logger.info(f"Phase Promotion: {target_node.id} -> FORMAL")

    session.current_mode = TutorMode.SOCRATIC # Default back to socratic if no proposal made
    
    trace.update({"action": action.value, "target": target_node.id, "reason": f"mode={session.exploration_mode}"})
    logger.info(f"Planner Reasoning: {trace}")
    
    # Update session rhythm
    if session.last_3_nodes and session.last_3_nodes[-1] == target_node.id:
        session.dept_on_node += 1
    else:
        session.dept_on_node = 1
    
    session.last_3_nodes.append(target_node.id)
    session.last_3_nodes = session.last_3_nodes[-3:]

    return PlannerDirective(action, target_node.id)


def plan_first_question(graph: GraphState) -> PlannerDirective:
    """Generate a directive for the very first question in a session."""
    unlocked = [n for n in graph.nodes if n.unlocked]
    weakest = min(unlocked, key=lambda n: n.mastery)
    return PlannerDirective(PlannerAction.REINFORCE, weakest.id)


# ── First-question helper ────────────────────────────────────

def plan_first_question(graph: GraphState) -> PlannerDirective:
    """Generate a directive for the very first question in a session.
    Starts with a neutral calibration prompt."""
    return PlannerDirective(PlannerAction.START_SESSION, "General")
