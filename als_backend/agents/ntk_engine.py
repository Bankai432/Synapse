# ──────────────────────────────────────────────────────────────
# Nanonautics ALS — Neural Tangent Kernel Engine (Phase 1)
# ──────────────────────────────────────────────────────────────
#
# Implements the linearized NTK model with cosine kernel as a
# proxy for gradient inner products.
#
# Mathematical specification:
#   Kernel:      K_ij = Θ(x_i, x_j) ≈ cosine(x_i, x_j)
#   Prediction:  f(x) = K(x, X) K⁻¹ y
#   Uncertainty: Var(f(x)) = Θ(x,x) - K(x,X) K⁻¹ K(X,x)
#   Similarity:  sim(i,j) = K_ij
#
# Phase 1 uses Socratic features only (d=5).
# Phase 2 will upgrade to true gradient inner products via MLP.
# ──────────────────────────────────────────────────────────────

import logging
import numpy as np
from typing import Optional

from config import (
    NTK_MIN_INTERACTIONS,
    NTK_WINDOW_SIZE,
    NTK_REG_LAMBDA,
)
from models import NTKInteraction

log = logging.getLogger(__name__)


# ── Kernel Function ──────────────────────────────────────────

def ntk_kernel(xi: np.ndarray, xj: np.ndarray) -> float:
    """Compute Θ(x_i, x_j) — the NTK between two feature vectors.

    Phase 1: cosine similarity as proxy for gradient inner product.
    Phase 2: will use ∇_θ f(x_i; θ₀)^T · ∇_θ f(x_j; θ₀).
    """
    norm_i = np.linalg.norm(xi)
    norm_j = np.linalg.norm(xj)
    if norm_i < 1e-10 or norm_j < 1e-10:
        return 0.0
    return float(np.dot(xi, xj) / (norm_i * norm_j))


# ── Kernel Matrix Construction ───────────────────────────────

def build_kernel_matrix(interactions: list[np.ndarray]) -> np.ndarray:
    """Construct the NTK matrix K ∈ R^{N×N}.

    K_ij = Θ(x_i, x_j) for all interaction pairs.
    The matrix is symmetric positive semi-definite by construction.
    """
    N = len(interactions)
    K = np.zeros((N, N))
    for i in range(N):
        for j in range(i, N):
            val = ntk_kernel(interactions[i], interactions[j])
            K[i, j] = val
            K[j, i] = val  # symmetric
    return K


def regularised_inverse(K: np.ndarray) -> np.ndarray:
    """Compute (K + λI)⁻¹ with Tikhonov regularisation for stability.

    This prevents numerical instability when K is near-singular
    (common when N is small or features are highly correlated).
    """
    N = K.shape[0]
    K_reg = K + NTK_REG_LAMBDA * np.eye(N)
    try:
        return np.linalg.inv(K_reg)
    except np.linalg.LinAlgError:
        log.warning("K matrix inversion failed; using pseudo-inverse fallback.")
        return np.linalg.pinv(K_reg)


# ── Prediction ───────────────────────────────────────────────

def predict(
    x_new: np.ndarray,
    X: list[np.ndarray],
    y: np.ndarray,
    K_inv: np.ndarray,
) -> float:
    """Predict mastery for a new interaction.

    f(x) = K(x, X) · K⁻¹ · y

    Args:
        x_new:  feature vector of the new interaction (R^d)
        X:      list of feature vectors of prior interactions (N × d)
        y:      target mastery values of prior interactions (R^N)
        K_inv:  precomputed regularised inverse of kernel matrix (N × N)

    Returns:
        Predicted mastery score, clamped to [0, 1].
    """
    k_row = np.array([ntk_kernel(x_new, xi) for xi in X])
    pred = float(k_row @ K_inv @ y)
    return max(0.0, min(1.0, pred))


def compute_uncertainty(
    x_new: np.ndarray,
    X: list[np.ndarray],
    K_inv: np.ndarray,
) -> float:
    """Compute predictive variance for a new interaction.

    Var(f(x)) = Θ(x,x) - K(x,X) · K⁻¹ · K(X,x)

    High variance means the model has not seen similar interactions —
    the planner should explore this concept.

    Returns:
        Non-negative variance. Clamped to ≥ 0 to guard against
        numerical errors producing tiny negative values.
    """
    k_row = np.array([ntk_kernel(x_new, xi) for xi in X])
    k_self = ntk_kernel(x_new, x_new)  # Θ(x, x) — always ≈ 1.0 for cosine
    var = k_self - float(k_row @ K_inv @ k_row)
    return max(0.0, var)


# ── Spectral Analysis ────────────────────────────────────────

def spectral_decomposition(K: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Eigendecomposition K = U Λ Uᵀ.

    Returns:
        eigenvalues:  Λ = diag(λ₁, ..., λ_N) in descending order
        eigenvectors: U (columns are eigenvectors)

    Used for mode dynamics analysis:
        f_t^(k) = y^(k) + exp(-λ_k · t) · (f_0^(k) - y^(k))
    """
    eigenvalues, eigenvectors = np.linalg.eigh(K)
    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    return eigenvalues[idx], eigenvectors[:, idx]


# ── Cross Kernel ─────────────────────────────────────────────

def cross_kernel(x_new: np.ndarray, X: list[np.ndarray]) -> np.ndarray:
    """Compute K(x, X) = [Θ(x,x₁), Θ(x,x₂), ..., Θ(x,x_N)] ∈ R^{1×N}."""
    return np.array([ntk_kernel(x_new, xi) for xi in X])


# ── Similarity ───────────────────────────────────────────────

def interaction_similarity(
    i: NTKInteraction,
    j: NTKInteraction,
) -> float:
    """sim(i, j) = K_ij — kernel similarity between two interactions."""
    xi = np.array(i.features)
    xj = np.array(j.features)
    return ntk_kernel(xi, xj)


# ── High-Level API ───────────────────────────────────────────

class NTKPredictor:
    """Stateless predictor that runs the full NTK pipeline on-demand.

    Usage per interaction:
        predictor = NTKPredictor()
        result = predictor.run(concept_id, x_new, ntk_history)
        # result.predicted_mastery, result.uncertainty, result.is_active
    """

    class Result:
        __slots__ = ("predicted_mastery", "uncertainty", "is_active",
                     "K_inv", "X", "y")

        def __init__(self, predicted_mastery: float, uncertainty: float,
                     is_active: bool, K_inv: Optional[np.ndarray] = None,
                     X: Optional[list] = None, y: Optional[np.ndarray] = None):
            self.predicted_mastery = predicted_mastery
            self.uncertainty = uncertainty
            self.is_active = is_active
            self.K_inv = K_inv
            self.X = X
            self.y = y

    def run(
        self,
        concept_id: str,
        x_new: np.ndarray,
        ntk_history: list[NTKInteraction],
    ) -> "NTKPredictor.Result":
        """Run NTK prediction for a concept.

        1. Filter history to this concept's interactions.
        2. Apply sliding window (keep last NTK_WINDOW_SIZE).
        3. Build K, compute K⁻¹.
        4. Predict mastery and compute uncertainty.

        If fewer than NTK_MIN_INTERACTIONS exist, returns inactive result.
        """
        # Filter to interactions for this concept
        concept_history = [
            h for h in ntk_history if h.concept_id == concept_id
        ]

        # Sliding window
        if len(concept_history) > NTK_WINDOW_SIZE:
            concept_history = concept_history[-NTK_WINDOW_SIZE:]

        # Not enough data — NTK is inactive, fall back to rules
        if len(concept_history) < NTK_MIN_INTERACTIONS:
            return self.Result(
                predicted_mastery=0.0,
                uncertainty=1.0,
                is_active=False,
            )

        # Build feature matrix and target vector
        X = [np.array(h.features) for h in concept_history]
        y = np.array([h.target_mastery for h in concept_history])

        # Build K and invert
        K = build_kernel_matrix(X)
        K_inv = regularised_inverse(K)

        # Predict and compute uncertainty
        pred = predict(x_new, X, y, K_inv)
        unc = compute_uncertainty(x_new, X, K_inv)

        log.debug(
            f"NTK [{concept_id}] N={len(X)}, "
            f"pred={pred:.4f}, unc={unc:.4f}"
        )

        return self.Result(
            predicted_mastery=pred,
            uncertainty=unc,
            is_active=True,
            K_inv=K_inv,
            X=X,
            y=y,
        )
