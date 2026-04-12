import logging
from typing import Dict, Any

from models import (
    EvaluateRequest,
    EvaluateResponse,
    NodeFrontend,
    SessionState
)
from memory.graph_store import GraphStore
from agents.graph_engine import GraphEngine
from agents.perception import perceive
from agents.evaluator import evaluate
from agents.transcriber import transcribe_audio
from agents.planner import plan, PlannerDirective, PlannerAction
from agents.tutor import generate_question, _get_client as _get_tutor_client
from groq import AsyncGroq

log = logging.getLogger(__name__)

async def run_evaluation_cycle(
    req: EvaluateRequest, 
    store: GraphStore, 
    engine: GraphEngine
) -> EvaluateResponse:
    """Full 8-step agentic cycle with session rhythm and personality."""
    
    # 1. Load graph
    graph = store.load(req.student_id)
    
    # 2. Synchronize SessionState with Request Modes
    if not graph.session_state:
        graph.session_state = SessionState()
    
    graph.session_state.exploration_mode = req.exploration_mode
    graph.session_state.personality_mode = req.personality_mode

    # 3. Handle Audio Transcription
    transcription = None
    if req.user_audio:
        transcription = await transcribe_audio(req.user_audio)
        
    # 4. Perception
    input_to_perceive = req.user_input
    if transcription:
        if input_to_perceive.strip():
            input_to_perceive = f"{input_to_perceive}\n\n[Transcribed Audio]: {transcription}"
        else:
            input_to_perceive = transcription
            
    clean_text = perceive(input_to_perceive)

    # 5. Calibration Check
    is_calibration = len(graph.session_state.history) == 0 and "calibrate your learning trajectory" in req.question

    # Context Preparation
    if is_calibration:
        expected_concepts = [n.id for n in graph.nodes]
    else:
        expected_concepts = [n.id for n in graph.nodes if n.unlocked]
        
    snapshot = {
        n.id: {"mastery": round(n.mastery, 3), "confidence": round(n.confidence, 3)}
        for n in graph.nodes if n.unlocked
    }

    # 6. Evaluator (LLM Call 1)
    eval_output = await evaluate(
        question=req.question,
        clean_text=clean_text,
        user_confidence=req.user_confidence,
        expected_concepts=expected_concepts,
        current_graph_snapshot=snapshot,
        image_data=req.user_image,
    )

    # 7. Calibration Handling
    if is_calibration:
        if not eval_output.concepts_used:
            # ── Calibration Bridge: Map out-of-domain to nearest STEAM ──
            client = _get_tutor_client()
            bridge_prompt = f"""You are a STEAM Bridge Agent. The student wants to learn about: "{clean_text}".
            Current STEAM Topics: {json.dumps(expected_concepts)}
            
            Find the SINGLE closest existing STEAM topic to bridge their interest. 
            If no remote connection exists, return "Newton's Laws" as a generic physics anchor.
            Return ONLY the topic name. No explanation."""
            
            try:
                resp = await client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": bridge_prompt}],
                    max_tokens=20
                )
                bridged_topic = resp.choices[0].message.content.strip()
                if bridged_topic in expected_concepts:
                    eval_output.concepts_used = [bridged_topic]
                    eval_output.gap = f"Mapping your interest in '{clean_text}' to our {bridged_topic} module."
                else:
                    raise ValueError("Topic not in graph")
            except Exception:
                next_question = "I am currently optimized for Science, Technology, Engineering, Arts, and Mathematics. Please specify a concept within these fields to begin."
                graph.session_state.history = [{"role": "assistant", "content": next_question}]
                store.save(req.student_id, graph)
                return EvaluateResponse(
                    gap="Input out of domain. STEAM context required.",
                    confidenceMismatch=False,
                    nextQuestion=next_question,
                    questionType="calibration",
                    conceptUpdates=[],
                    newNodes=[],
                    newLinks=[],
                )
        if eval_output.concepts_used:
            target_id = eval_output.concepts_used[0]
            node_map = {n.id: n for n in graph.nodes}
            target_node = node_map.get(target_id)
            if target_node:
                target_node.unlocked = True
                target_node.session_activated = True
                
                from seed.concept_graph import get_prerequisites
                for p_id in get_prerequisites(target_id):
                    if p_id in node_map:
                        node_map[p_id].unlocked = True

    # 8. Graph Engine (Math)
    if is_calibration:
        deltas, new_nodes, new_links, unlock_reasons = [], [], [], []
        unlocked = [n for n in graph.nodes if n.unlocked and n.id in eval_output.concepts_used]
        new_nodes = [
            NodeFrontend(
                id=n.id, field=n.field, mastery=round(n.mastery*100,2),
                confidence=round(n.confidence*100,2), decay=n.decay, error_rate=n.error_rate
            ) for n in unlocked
        ]
    else:
        graph, deltas, new_nodes, new_links, unlock_reasons = engine.update(
            graph, eval_output, req.user_confidence
        )
        if unlock_reasons:
            eval_output.gap = f"{eval_output.gap}\n\n[System Update]: " + " ".join(unlock_reasons)

    # 9. Planner
    if is_calibration:
        directive = PlannerDirective(PlannerAction.REINFORCE, eval_output.concepts_used[0])
    else:
        directive = plan(graph, eval_output, req.user_confidence)

    # 10. Tutor (LLM Call 2)
    next_question, question_type = await generate_question(
        directive, eval_output.gap, graph
    )

    # Update History
    new_history = [
        {"role": "user", "content": clean_text},
        {"role": "assistant", "content": next_question}
    ]
    graph.session_state.history.extend(new_history)
    graph.session_state.history = graph.session_state.history[-4:]

    # Persist
    store.save(req.student_id, graph)

    return EvaluateResponse(
        gap=eval_output.gap,
        confidenceMismatch=eval_output.confidenceMismatch,
        nextQuestion=next_question,
        questionType=question_type,
        transcription=transcription,
        conceptUpdates=deltas,
        newNodes=new_nodes,
        newLinks=new_links,
    )
