"""
CyberSentinel AI — Trust Scoring Engine
Author: CyberSentinel ML-LAB

Computes a deterministic trust score based on:
  1. Model confidence (calibrated probability)
  2. Class separation margin
  3. Behavioral anomaly (feature deviation)

Trust score is INDEPENDENT of raw confidence alone.
"""

import numpy as np
import logging

logger = logging.getLogger("trust_engine")


def compute_trust_score(
    prob: float,
    attack_type: str,
    feature_vector: "np.ndarray",
    mean: "np.ndarray",
    scale: "np.ndarray",
    margin: float = 0.0,
) -> dict:
    """
    Compute a multi-signal Zero Trust score.

    Parameters:
        prob         (float):        Calibrated probability of the prediction.
        attack_type  (str):          Classified attack label (or 'Normal').
        feature_vector (np.ndarray): Scaled input feature values.
        mean         (np.ndarray):   Scaler means (stored on pipeline).
        scale        (np.ndarray):   Scaler std devs (stored on pipeline).
        margin       (float):        Top-2 multiclass probability margin (0–1).

    Returns:
        dict with keys: trust_score, risk_level, confidence, anomaly_score
    """
    try:
        # ── 1. Anomaly component: exp(-mean(|scaled_features|)) ──────────────
        # Uses already-scaled features so no re-standardisation needed.
        # Values near zero → normal; large values → anomalous → low component.
        # Cap at 10 to prevent exp(-x) collapsing to ~0 for extreme flows.
        abs_scaled = np.abs(np.nan_to_num(feature_vector, nan=0.0, posinf=5.0, neginf=-5.0))
        anomaly_score = float(min(np.mean(abs_scaled), 10.0))
        anomaly_component = float(np.exp(-anomaly_score))   # in (0, 1]

        # ── 2. Clamp inputs ───────────────────────────────────────────────────
        confidence = float(np.clip(prob, 0.0, 1.0))
        margin_val = float(np.clip(margin, 0.0, 1.0))

        # ── 3. Multi-signal weighted formula ─────────────────────────────────
        #   trust_score = 0.5 * confidence + 0.3 * margin + 0.2 * anomaly
        trust_score = (
            0.5 * confidence
            + 0.3 * margin_val
            + 0.2 * anomaly_component
        )

        # ── 4. Clamp to [0, 1] ────────────────────────────────────────────────
        trust_score = float(np.clip(trust_score, 0.0, 1.0))

        # ── 5. Risk mapping: HIGH trust → LOW risk (correct semantics) ────────
        #       LOW trust  → HIGH risk (system is uncertain / anomalous)
        if trust_score >= 0.7:
            risk_level = "LOW"
        elif trust_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "trust_score": round(trust_score, 4),
            "risk_level": risk_level,
            "confidence": confidence,
            "anomaly_score": round(anomaly_score, 4),
        }

    except Exception as exc:
        logger.error("Trust computation failed: %s", exc)
        return {
            "trust_score": 0.5,
            "risk_level": "MEDIUM",
            "confidence": float(prob),
            "anomaly_score": 0.0,
        }
