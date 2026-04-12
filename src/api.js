// ──────────────────────────────────────────────────────────────
// Nanonautics ALS — API Client
// ──────────────────────────────────────────────────────────────
//
// All requests go through the Vite proxy (/api → localhost:8000).
// No hardcoded backend URLs — works in development and production
// as long as the reverse proxy is configured correctly.
// ──────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_BACKEND_URL ? `${import.meta.env.VITE_BACKEND_URL}/api` : "/api";
const HEALTH_BASE = import.meta.env.VITE_BACKEND_URL || "";

/**
 * Parse the JSON response body and throw a descriptive error on failure.
 * @param {Response} res
 * @returns {Promise<any>}
 */
async function handleResponse(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // Body wasn't JSON — use status text
      detail = res.statusText || detail;
    }
    throw new Error(detail);
  }
  return res.json();
}

export class EvaluationAPI {
  /**
   * Load the student's lifetime knowledge graph.
   * Called once on app mount.
   *
   * @param {string} studentId
   * @returns {Promise<{ nodes: NodeFrontend[], links: LinkFrontend[], sessionGraph: string[] }>}
   */
  static async getGraph(studentId) {
    const res = await fetch(
      `${API_BASE}/graph?student_id=${encodeURIComponent(studentId)}`
    );
    return handleResponse(res);
  }

  /**
   * Generate the first Socratic question for a new session.
   *
   * @param {string} studentId
   * @returns {Promise<{ nextQuestion: string, questionType: string, targetConcept: string }>}
   */
  static async getFirstQuestion(studentId) {
    const res = await fetch(
      `${API_BASE}/next-question?student_id=${encodeURIComponent(studentId)}`
    );
    return handleResponse(res);
  }

  /**
   * Submit a student answer and run the full 8-step evaluation pipeline.
   *
   * @param {string} question    - the question that was asked
   * @param {string} input       - the student's raw answer text
   * @param {number} confidence  - self-reported confidence (0–100)
   * @param {string} studentId
   * @param {string} explorationMode
   * @param {string} personalityMode
   * @param {string} image       - base64 data URL
   * @param {string} audio       - base64 data URL
   * @returns {Promise<EvaluateResponse>}
   */
  static async evaluateResponse(question, input, confidence, studentId, explorationMode, personalityMode, image, audio) {
    const res = await fetch(`${API_BASE}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        user_input: input,
        user_confidence: confidence,
        student_id: studentId,
        exploration_mode: explorationMode,
        personality_mode: personalityMode,
        user_image: image,
        user_audio: audio,
      }),
    });
    return handleResponse(res);
  }

  /**
   * Liveness check — useful for showing connection status in the UI.
   * @returns {Promise<{ status: string, model: string }>}
   */
  static async healthCheck() {
    const res = await fetch(`${HEALTH_BASE}/health`);
    return handleResponse(res);
  }
}
