import asyncio
import os
import uuid
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from groq import AsyncGroq
from models import EvaluateRequest
from memory.graph_store import GraphStore
from agents.graph_engine import GraphEngine
from agents.planner import plan_first_question
from agents.tutor import generate_question
from services.evaluation_pipeline import run_evaluation_cycle
from config import GRAPH_STORE_DIR

# Verify API Key
if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY environment variable is required.")

groq_client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"))

ROLE_PROMPTS = {
    "struggling": "You are a student learning STEM subjects. You are easily confused, write short answers, and often use 'magic' logic (e.g., 'magic wagons' or 'special scales') when you don't understand the physics. You also make category errors, like thinking a robot is a type of animal because it moves. You use hedging language like 'I think' and 'Um' frequently because you are afraid of being wrong.",
    "confident": "You are an overconfident student. You write brief, assertive answers and try to sound smart, but you occasionally miss subtle edge cases.",
    "methodical": "You are a highly methodical student. You explain your thought process clearly, break down problems into steps, but you are not perfect."
}

async def generate_student_response(role_prompt: str, question: str, chat_history: list) -> str:
    messages = [
        {"role": "system", "content": role_prompt + "\nAnswer the tutor's question directly, playing your character. Output only the text of your answer, nothing else."},
    ]
    for msg in chat_history[-6:]: # Keep only last few turns for context window
        messages.append(msg)
    messages.append({"role": "user", "content": question})
    
    response = await groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=250,
        temperature=0.7
    )
    return response.choices[0].message.content

async def run_simulation(role_name: str, num_interactions: int, log_file):
    student_id = f"sim_{role_name}_{uuid.uuid4().hex[:6]}"
    role_prompt = ROLE_PROMPTS[role_name]
    
    # Initialize backend components
    store = GraphStore(GRAPH_STORE_DIR)
    engine = GraphEngine()
    
    log_file.write(f"\n{'='*50}\nStarting Session for Student: {student_id} (Role: {role_name})\n{'='*50}\n")
    print(f"\nStarting session for '{student_id}'...")
    
    # Get first question
    graph = store.load(student_id)
    first_directive = plan_first_question(graph)
    current_question, q_type = await generate_question(first_directive, "", graph)
    
    log_file.write(f"Tutor [Next Type: {q_type}]: {current_question}\n\n")
    
    chat_history = []
    
    for i in range(num_interactions):
        print(f"  Interaction {i+1}/{num_interactions}...", end="", flush=True)
        # Generate Student Answer
        student_ans = await generate_student_response(role_prompt, current_question, chat_history)
        log_file.write(f"Student [{i+1}]: {student_ans}\n\n")
        
        chat_history.append({"role": "assistant", "content": current_question})
        chat_history.append({"role": "user", "content": student_ans})
        
        # Evaluate
        req = EvaluateRequest(
            student_id=student_id,
            question=current_question,
            user_input=student_ans,
            user_confidence=50,
            exploration_mode="Socratic",
            personality_mode="Socratic"
        )
        
        eval_res = await run_evaluation_cycle(req, store, engine)
        
        log_file.write(f"-- Evaluation Report --\nGap Analysis: {eval_res.gap}\n")
        if eval_res.conceptUpdates:
            for upd in eval_res.conceptUpdates:
                log_file.write(f"  Concept Update [{upd.id}]: Mastery Delta = {upd.masteryDelta:+.2f}\n")
        else:
            log_file.write("  (No concept updates generated)\n")
        log_file.write(f"-----------------------\n\n")
        
        if not eval_res.nextQuestion:
            log_file.write("Session ended by tutor.\n")
            print(" ended.")
            break
            
        current_question = eval_res.nextQuestion
        q_type = eval_res.questionType
        log_file.write(f"Tutor [{i+1}] [Type: {q_type}]: {current_question}\n\n")
        print(" done.")
        
        # Sleep slightly to avoid rate linking
        await asyncio.sleep(0.5)

async def main():
    # Configuration
    role = "struggling"
    runs = 1
    interactions_per_run = 50
    
    log_filename = "simulate_log.txt"
    log_path = os.path.join(os.path.dirname(__file__), log_filename)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n\n{'#'*60}\nSimulation Batch started at {datetime.now().isoformat()}\n{'#'*60}\n")
        
    for r in range(runs):
        print(f"--- RUN {r+1} of {runs} ---")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- RUN {r+1}/{runs} ---\n")
            await run_simulation(role, interactions_per_run, f)
            f.flush()
            
    print(f"\nSimulation complete. Results appended to {log_path}")

if __name__ == "__main__":
    asyncio.run(main())
