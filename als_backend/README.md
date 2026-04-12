# Nanonautics ALS Backend

Agentic Learning System — a personalized Socratic tutor for competitive programming that maintains a live mathematical knowledge graph of the student's understanding.

## Quick Start

### 1. Install dependencies

```bash
cd als_backend
pip install -r requirements.txt
```

### 2. Set your Groq API key

Copy the example and fill in your key:

```bash
cp .env.example .env
# then edit .env and replace the placeholder with your real key
```

Or set it directly as an environment variable:

```powershell
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_..."

# Linux / macOS
export GROQ_API_KEY="gsk_..."
```

Get a free key at: https://console.groq.com/

### 3. Run the backend server

```bash
cd als_backend
uvicorn main:app --reload --port 8000
```

### 4. Run the frontend (separate terminal)

```bash
# from the project root (my-app/)
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.  
The API will be available at `http://localhost:8000`.

---

## API Endpoints

| Method | Path                | Purpose                                                                                      |
| ------ | ------------------- | -------------------------------------------------------------------------------------------- |
| GET    | `/health`           | Liveness check. Returns `{ status: "ok", model: "..." }`.                                   |
| GET    | `/api/graph`        | Load the student's lifetime knowledge graph, apply temporal decay, reset session flags.      |
| GET    | `/api/next-question`| Generate the first Socratic question for a new learning session.                             |
| POST   | `/api/evaluate`     | Full 8-step agentic cycle: Perception → Evaluator (LLM) → Graph Engine → Planner → Tutor.   |

All student-scoped endpoints require `?student_id=<id>` query parameter.  
`student_id` must match `^[a-zA-Z0-9_-]{1,64}$`.

---

## Architecture

```
Student Answer
  → Perception (text normalize)
  → Evaluator + Feedback (Groq LLM, Call 1)  — scores correctness, extracts concepts
  → Graph Engine (pure math)                  — mastery/confidence/Hebbian update
  → Planner (deterministic rules)             — selects next pedagogical directive
  → Tutor (Groq LLM, Call 2)                 — generates Socratic question
  → Persist (JSON file, file-locked)
```

- **2 LLM calls** per `/api/evaluate` invocation, always
- **All pedagogical decisions** made by deterministic Planner rules — not the LLM
- **Persistent JSON-file store** per student: `student_graphs/graph_{student_id}.json`
- **Internal scale**: 0.0–1.0 | **Frontend scale**: 0–100
- **File locking**: concurrent requests never corrupt the same student's graph
- **Retry with back-off**: LLM calls retry up to 3× on transient errors

---

## Environment Variables

| Variable        | Required | Description                                          |
| --------------- | -------- | ---------------------------------------------------- |
| `GROQ_API_KEY`  | ✅ Yes   | Groq API key (get from https://console.groq.com/)   |
| `CORS_ORIGINS`  | No       | Comma-separated allowed origins (default `*`)        |

---

## Tuning Hyperparameters

All tunable constants are in `config.py`. Key values:

| Constant                           | Default     | Meaning                                       |
| ---------------------------------- | ----------- | --------------------------------------------- |
| `LAMBDA_`                          | `0.0000011` | Decay rate per second (~50% after 7 days)     |
| `SPACED_REPETITION_DECAY_THRESHOLD`| `259200`    | 3 days in seconds — triggers spaced rep       |
| `ETA_1`                            | `0.10`      | Mastery learning rate per interaction         |
| `UNLOCK_MASTERY_MIN`               | `0.40`      | Minimum mastery for prerequisite unlock gate  |
| `UNLOCK_EDGE_STRENGTH_MIN`         | `0.25`      | Minimum edge strength for unlock gate         |

---

## Deployment

### Simple (single server)

```bash
# Production backend
cd als_backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# Production frontend (build then serve)
cd ..
npm run build
# Serve dist/ with any static host (Nginx, Caddy, Vercel, Netlify)
```

**Note:** Use `--workers 1` with the file-based JSON store. For multi-worker
deployments, switch to a SQLite or Postgres backend.

### Environment for production

```bash
GROQ_API_KEY=gsk_...
CORS_ORIGINS=https://your-frontend-domain.com
```
