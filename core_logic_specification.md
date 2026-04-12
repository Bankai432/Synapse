# Nanonautics ALS — Core Logic Specification

This document defines the mathematical, logical, and agentic foundations of the Agentic Learning System (ALS). It is designed to serve as the "Source of Truth" for the engine's behavior, allowing for modifications to be made here and subsequently implemented in the codebase.

---

## 1. System Architecture: The Agentic Cycle

The ALS operates on a per-interaction loop, orchestrated in `main.py`. Each "turn" follows a strict 8-step sequence:

1.  **Persistence**: Load the student's `GraphState` and `SessionState` (rhythm, modes, history) from the filesystem.
2.  **Perception**: Normalize raw student input text using `perception.py`.
3.  **Context Construction**: 
    - Identify "Expected Concepts" (all currently unlocked nodes).
    - Generate a "Graph Snapshot" (current mastery/confidence levels).
    - Capture conversation history (last 2-3 exchanges).
4.  **Evaluation (LLM)**: `evaluator.py` analyzes the response against expectations, generates numeric scores, identifies "novel connections", and produces a semantic "gap" string.
5.  **Graph Engine (Math)**: `graph_engine.py` applies deterministic formulas to update node and edge states, explicitly rewarding connection-making.
6.  **Planning (Rules)**: `planner.py` evaluates graph state AND `session_rhythm` against priority rules. Outputs a `PlannerDirective` + `ReasoningTrace`.
7.  **Tutoring (LLM)**: `tutor.py` synthesizes a response based on the directive, `personality_mode`, and the conversational context.
8.  **Commitment**: Persist the updated graph and session state, then return the response.

---

## 2. Statistical State Tracking (The "Stats")

The system tracks student state using five core variables per concept node ($i$).

| Stat | Range | Description | Formula / Logic |
| :--- | :--- | :--- | :--- |
| **Mastery ($m_i$)** | 0.0 – 1.0 | Pure technical proficiency. | $m_i = m_i + \eta_1 \cdot (\text{corr} \cdot \text{reason}) + \eta_3 \cdot \text{len}(\text{novel\_conn}) \cdot \text{corr}$ |
| **Error Rate ($e_i$)** | 0.0 – 1.0 | Frequency of mistakes/misconceptions. | $e_i = e_i + \eta_2 \cdot (1 - \text{correctness})$ |
| **Confidence ($c_i$)** | 0.0 – 1.0 | Student's perceived vs. actual ability. | $c_i = \alpha \cdot \text{self\_report} + (1 - \alpha) \cdot \text{correctness}$ |
| **Decay ($d_i$)** | 0.0 – 1.0 | Last applied forgetting factor. | $m_i = m_i \cdot \exp(-\lambda \cdot \Delta t)$ |
| **Edge Strength ($w_{ij}$)** | 0.0 – 1.0 | Hebbian link between concepts. | $\Delta w_{ij} = \eta_w \cdot a_i \cdot a_j \cdot \text{correctness}$ |

### 2.1 Logic Notes
- **Mastery Update**: Includes a "Connection Bonus" ($\eta_3$). Students are rewarded more for spontaneously linking concepts than for simple correct answers.
- **Confidence Blend**: Uses $\alpha$ (0.70) to prioritize self-report while anchoring in objective performance.
- **Hebbian Learning**: Strengthens links only when concepts are used together correctly.

### 2.2 Session Rhythm
To prevent "railroading" and ensure natural flow, the system tracks session-level dynamics:

| Parameter | Description | Rule / Constraint |
| :--- | :--- | :--- |
| `dept_on_node` | Turns spent on current node. | Max 3 turns before a forced pivot. |
| `last_3_nodes` | History of recent target nodes. | Used to prevent immediate loops. |
| `momentum` | `deepening` \| `drifting` \| `bridging` | Governs the type of next question. |
| `turns_since_conn` | Turns since last `BUILD_CONNECTION`. | Every 5-7 turns, a connection attempt is forced. |

---

## 3. Unlocking & Frontier Exploration

The Knowledge Graph is structured in Tiers (1–5). A concept node remains "locked" (invisible to the student) until its prerequisites are mastered.

**The Unlock Condition:**
A node $i$ is unlocked if:
1.  It is a Tier-1 foundation node (Arrays, Strings, etc.).
2.  **OR** all its prerequisite parents have:
    - `Mastery` $\ge$ 0.40
    - `Edge Strength` (to the child) $\ge$ 0.25

---

## 4. Session & Personality Control

The learning experience is governed by two session-level parameters that modify the behavior of the Planner and Tutor agents.

### 4.1 Exploration Modes (Planner Logic)
| Mode | Behavior | Student Experience |
| :--- | :--- | :--- |
| **Depth** | Exhaustive drilling on a single node (Def → App → Debug). | Intense focus, mastery-first. |
| **Float** | One node + all immediate neighbors. | Conceptual web-building. |
| **Drift** | Follows student's novel connections / Hebbian activations. | Emergent, creative flow. |
| **Socratic** | **(Default)** Rhythmic mix of deepening and bridging. | Natural, balanced dialogue. |

### 4.2 Personality Modes (Tutor Voice)
| Mode | Tone / Constraints | Example |
| :--- | :--- | :--- |
| **Socratic** | Probing, uses silence, avoids direct answers. | "That's an interesting framing. What happens if n=0?" |
| **Nerdy** | Enthusiastic, theory-heavy, uses analogies. | "Oh interesting! You're describing a call stack. Like how an OS..." |
| **Strict** | Terse, clinical, focused on pure logical correctness. | "Incorrect. Define the termination condition." |
| **Collaborative**| Thinks 'out loud', works alongside the student. | "Let me think about that... if the base case is optional..." |

---

## 5. Agent Engineering & Prompt Layouts

### 5.1 Evaluator Agent (Llama-3.3-70b)
- **Role**: Technical score-keeper and connection detector.
- **Connection Detection**: Specifically looks for student-initiated links between the current node and other concepts in the graph.
- **Semantic Gap**: Restricted to "compiler-error" style. Forbidden words: *good, try, nice*.

### 5.2 Planner Agent (Rule-Based + Reasoning Trace)
- **Input**: GraphState + SessionRhythm + ExplorationMode.
- **Transparency**: Every decision must emit a **Reasoning Trace** (JSON):
  ```json
  {
    "action": "CHALLENGE_MISCONCEPTION",
    "target": "Recursion",
    "reason": "user_confidence=0.75 > mastery=0.31",
    "rhythm_influence": "depth_limit_reached, forcing pivot",
    "alternatives": ["REINFORCE", "ADVANCE"]
  }
  ```
- **Strategy Selection**: Modified by `session_rhythm` to force bridging questions during topic pivots.

### 5.3 Tutor Agent (Llama-3.3-70b)
- **Role**: Conversational voice.
- **Context Awareness**: Receives the last 2-3 message exchanges to maintain conversational flow and reference student's earlier points.
- **Constraint**: No "hollow" encouragement, but allowed to express curiosity and make technical observations.
- **Instruction**: Synthesizes the `PlannerDirective` through the lens of the current `PersonalityMode`.

---

## 6. Core Hyperparameters (Modification Schema)

| Constant | Default | Effect if Increased |
| :--- | :--- | :--- |
| `ETA_1` | 0.10 | Students gain mastery faster (more lenient). |
| `ETA_2` | 0.05 | Errors accumulate faster (more punishing). |
| `ETA_3` | 0.15 | **(New)** Novel connections provide a larger mastery boost. |
| `ALPHA` | 0.70 | System "trusts" student self-reports more. |
| `ETA_W` | 0.08 | Concepts become linked more quickly. |
| `LAMBDA_` | 1.1e-6 | Memory fades faster (stricter review requirements). |
| `UNLOCK_MASTERY_MIN` | 0.40 | Progression bottleneck becomes tighter. |

---

## 7. Use of LLMs

| Agent | Model | Justification |
| :--- | :--- | :--- |
| **Evaluator** | Llama 3.3 70B | High reasoning for fallacy detection and novel connection mapping. |
| **Tutor** | Llama 3.3 70B | Nuanced control over personality and context synthesis. |

*All other agents (Perception, Planner, Graph Engine) are deterministic Python or rule-based logic to ensure auditability.*
