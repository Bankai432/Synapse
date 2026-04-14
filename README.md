# Agentic Learning System (ALS) — Nanonautics

A powerful, personalized Socratic tutor for Science, Technology, Engineering, Arts, and Mathematics (STEAM). The ALS uses an agentic evaluation pipeline to guide students through a mastery-based knowledge graph.

## Features
- **Pedagogical Policy Engine**: Dynamic mode-switching (Socratic, Direct, Repair).
- **Ontological Grounding**: Detects and corrects "magic thinking" or category errors.
- **Knowledge Laddering**: Ensures students master concrete concepts before moving to abstract formalisms.
- **High-Performance Visuals**: React-based force-directed graph with smooth mastery-based color gradients.

## Architecture
- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite + Tailwind CSS
- **Interactions**: Groq (Llama 3.1 & Vision) for reasoning and tutoring.

## Local Setup

### Backend
1. Navigate to `als_backend/`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the server: `uvicorn main:app --reload`

### Frontend
1. Run `npm install`
2. Run `npm run dev`

## Deployment (Production)

This project is structured for easy deployment on **Render** (Backend) and **Vercel** (Frontend).

### Backend (Render)
- **Root Directory**: `als_backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
- **Blueprint**: See `als_backend/render.yaml` for configuration.

### Frontend (Vercel)
- **Framework**: Vite
- **Environment Variable**: `VITE_BACKEND_URL` (Set to your Render URL)
