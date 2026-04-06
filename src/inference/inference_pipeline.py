"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Inference Pipeline (Stage 7)
Author: CyberSentinel ML-LAB

Single entry-point for production inference.
Accepts raw network flow data (as a DataFrame or dict), runs the full
cascade, and returns a structured PolicyDecision per row.

Cascade:
    raw input
        ↓  validate + select features
        ↓  StandardScaler (loaded from models/scaler.pkl)
        ↓  Binary Classifier → P(attack)
        ↓  if binary == 1:  Multi-class Classifier → attack_type
        ↓  Policy Mapper → ALLOW / QUARANTINE / DENY
        ↓  PolicyDecision

Public API:
    pipeline = InferencePipeline()            # load all artifacts once
    decision  = pipeline.predict_one(row)     # single flow dict → PolicyDecision
    decisions = pipeline.predict(df)          # DataFrame → list[PolicyDecision]
"""

from __future__ import annotations

import logging
import time
import os
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd

from src.features.preprocessor import load_scaler
from src.training.multiclass_trainer import load_multiclass_model
from src.policy.policy_mapper import PolicyDecision, PolicyMapper
from src.core.trust_engine import compute_trust_score
from src.core.feedback_logger import log_feedback_async
from fastapi import HTTPException
import joblib

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("inference_pipeline")

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

from src.core.paths import DATA_DIR, MODELS_DIR

PROCESSED_DIR = DATA_DIR / "processed"


# ==================================================================
# InferencePipeline
# ==================================================================


class InferencePipeline:
    """
    End-to-end inference pipeline for CyberSentinel-AI.

    Loads all trained artifacts once at instantiation, then exposes
    ``predict()`` (batch) and ``predict_one()`` (single-row) methods.

    Parameters
    ----------
    features_path : Path, optional
        Path to selected_features.json.  Auto-resolved if not given.
    scaler_path : Path, optional
        Path to scaler.pkl.  Auto-resolved if not given.
    binary_model_dir : Path, optional
        Directory containing the binary model.pkl.
    multiclass_model_dir : Path, optional
        Directory containing the multi-class model.pkl + label_encoder.pkl.
    policy_config_path : Path, optional
        Path to policy.yaml.  Auto-resolved if not given.
    binary_threshold : float
        Probability threshold above which a flow is classified as Attack.
        Default 0.5.  Lower to reduce false negatives; raise to cut false positives.

    Examples
    --------
    >>> pipeline = InferencePipeline()
    >>> df = pd.read_csv("new_flows.csv")
    >>> decisions = pipeline.predict(df)
    >>> for d in decisions:
    ...     print(d)
    """

    def __init__(
        self,
        features_path: Optional[Path] = None,
        scaler_path: Optional[Path] = None,
        binary_model_dir: Optional[Path] = None,
        multiclass_model_dir: Optional[Path] = None,
        policy_config_path: Optional[Path] = None,
        binary_threshold: float = 0.3,
    ) -> None:
        t0 = time.time()
        logger.info("Loading inference artifacts…")

        self._threshold = float(os.getenv("BINARY_THRESHOLD", binary_threshold))
        
        # 1. Single Source of Truth Validation (CRITICAL)
        # Enforce metadata.json as canonical. Fail-fast if models/binary/features.pkl differs.
        import json
        meta_path = MODELS_DIR / "binary" / "metadata.json"
        
        try:
            with open(meta_path, "r") as f:
                meta_json = json.load(f)
                json_features = meta_json.get("data", {}).get("features", [])
        except Exception as e:
            logger.error(f"Failed to load canonical metadata.json: {e}")
            raise

        self._features: list[str] = joblib.load(MODELS_DIR / "binary" / "features.pkl")
        
        if json_features != self._features:
            error_msg = (
                f"CRITICAL: Feature mismatch! "
                f"metadata.json ({len(json_features)}) != features.pkl ({len(self._features)}). "
                "Inconsistent retraining artifacts detected. Failing fast."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        self._scaler = load_scaler(scaler_path)
        import onnxruntime as rt
        
        self._binary_sess = rt.InferenceSession(
            str(MODELS_DIR / "binary" / "base_binary_model.onnx"),
            providers=["CPUExecutionProvider"]
        )
        self._mc_sess = rt.InferenceSession(
            str(MODELS_DIR / "multiclass" / "multiclass_model.onnx"),
            providers=["CPUExecutionProvider"]
        )
        # Note: ONNX used for speed, sklearn model used for calibrated probabilities
        self._calibrated_binary = joblib.load(MODELS_DIR / "binary" / "calibrated_binary_model.pkl")
        self.mean = self._scaler.mean_
        self.scale = self._scaler.scale_
        _, self._encoder = load_multiclass_model(multiclass_model_dir)
        self._policy = PolicyMapper(policy_config_path)

        logger.info(
            "InferencePipeline ready — %d features  threshold=%.2f  (%.2fs)",
            len(self._features),
            self._threshold,
            time.time() - t0,
        )

    # ----------------------------------------------------------------
    # Public methods
    # ----------------------------------------------------------------

    def predict_one(self, row: Union[dict, pd.Series]) -> PolicyDecision:
        """
        Run the full inference cascade on a single network flow.

        Parameters
        ----------
        row : dict | pd.Series
            Feature values keyed by feature name.  Missing features
            are filled with 0.0; extra columns are ignored.

        Returns
        -------
        dict
            Full structured policy decision with trust telemetry.
        """
        if isinstance(row, dict):
            row = pd.Series(row)
        df_single = row.to_frame().T
        results = self.predict(df_single)
        
        # Unpack for specific return structure requested by user
        res = results[0]

        return {
            "prediction": res["prediction"],
            "attack_type": res["attack_type"],
            "action": res["action"],
            "confidence": float(res["confidence"]),
            "margin": float(res["margin"]),
            "attack_proba": res["attack_proba"],
            "trust": {
                "trust_score": float(res["trust"]["trust_score"]),
                "risk_level": str(res["trust"]["risk_level"])
            }
        }

    def predict(self, df: pd.DataFrame) -> list[PolicyDecision]:
        """
        Run the full inference cascade on a batch of network flows.

        Parameters
        ----------
        df : pd.DataFrame
            Each row is one network flow.  The DataFrame must contain
            (at minimum) the columns in the selected feature list.
            Extra columns are silently ignored.

        Returns
        -------
        list[PolicyDecision]
            One decision per input row, in input order.
        """
        if df.empty:
            return []

        t0 = time.time()

        # ---- 1. Validate + select features --------------------------
        x = self._prepare_features(df)

        # ---- 2. Scale -----------------------------------------------
        x_scaled = pd.DataFrame(
            self._scaler.transform(x),
            columns=self._features,
            dtype=np.float32,
        )

        # ---- 3. Binary prediction (Optimized: ONNX + Calibrated Trust) ----
        # Rationale: ONNX is used for high-speed standardized inference. 
        # CalibratedClassifierCV (Sklearn) is run concurrently ONLY because it provides 
        # high-fidelity "trust scores" required by the Policy Engine which raw 
        # binary ONNX outputs often lack in specialized production builds.
        
        x_scaled = x_scaled[self._features].copy()
        x_numpy = x_scaled.to_numpy(dtype=np.float32)
        
        # Perform primary binary classification via ONNX
        input_b = self._binary_sess.get_inputs()[0].name
        outputs_b = self._binary_sess.run(None, {input_b: x_numpy})
        
        if len(outputs_b) < 2:
            raise RuntimeError("ONNX output malformed")
        
        # Binary prediction (0/1) directly from ONNX output to avoid redundant compute
        # logic in the primary classification branch.
        binary_preds = outputs_b[0].tolist()
        
        # Confidence/Trust scores from Calibrated model (No redundant compute applied:
        # the model is run specifically for the probability distribution).
        attack_proba_col = self._calibrated_binary.predict_proba(x_scaled)[:, 1]  
        attack_proba_col = np.clip(attack_proba_col, 0.0, 1.0)
        
        binary_preds = np.array(binary_preds).astype(int)
        binary_confidences = np.where(
            binary_preds == 1, attack_proba_col, 1.0 - attack_proba_col
        )

        attack_indices = np.nonzero(binary_preds == 1)[0]
        attack_types: list[Optional[str]] = [None] * len(df)
        attack_probas: list[Optional[dict[str, float]]] = [None] * len(df)
        margins: list[float] = [0.0] * len(df)
        if len(attack_indices) > 0:
            x_attack = x_scaled.iloc[attack_indices]
            x_attack_np = x_attack.to_numpy(dtype=np.float32)
            input_m = self._mc_sess.get_inputs()[0].name
            
            mc_outputs = self._mc_sess.run(None, {input_m: x_attack_np})
            
            if len(mc_outputs) < 2:
                raise RuntimeError("ONNX output malformed")
                
            mc_preds = mc_outputs[0]
            mc_proba = mc_outputs[1]  # List of dicts in ONNX output format
            class_names = self._encoder.classes_.tolist()

            for local_i, global_i in enumerate(attack_indices):
                predicted_class_idx = mc_preds[local_i]
                attack_types[global_i] = self._encoder.inverse_transform(
                    [predicted_class_idx]
                )[0]
                # Format probas explicitly based on ONNX dictionary structure
                raw_probas = mc_proba[local_i] # ONNX maps
                sorted_vals = sorted(raw_probas.values(), reverse=True)
                margins[global_i] = float(sorted_vals[0] - sorted_vals[1] if len(sorted_vals) > 1 else sorted_vals[0])

                attack_probas[global_i] = {
                    cls: round(float(raw_probas.get(j, 0.0)), 6)
                    for j, cls in enumerate(class_names)
                }

        # ---- 5. Enterprise Zero-Trust Decision Layer -----------------
        final_decisions: list[dict] = []
        
        for i in range(len(df)):
            # Extract feature vector for this row
            feature_vector = x_numpy[i]
            
            # CRITICAL VALIDATION (Production Shape Check)
            if len(feature_vector) != len(self.mean):
                raise ValueError(
                    f"CRITICAL: Feature length mismatch. "
                    f"Expected {len(self.mean)}, got {len(feature_vector)}"
                )
            
            # Compute trust score via Enterprise Engine (multi-signal)
            trust_data = compute_trust_score(
                prob=float(binary_confidences[i]),
                attack_type=attack_types[i] or "Normal",
                feature_vector=feature_vector,
                mean=self.mean,
                scale=self.scale,
                margin=float(margins[i]),
            )

            computed_ts = float(trust_data["trust_score"])
            confidence_val = float(binary_confidences[i])

            prediction_label = "Attack" if binary_preds[i] == 1 else "Normal"

            # ── Confidence-primary policy (trust is auxiliary / explainability only) ──
            if prediction_label == "Attack":
                if confidence_val >= 0.85:
                    final_action = "DENY"
                    risk_level   = "HIGH"
                elif confidence_val >= 0.6:
                    final_action = "QUARANTINE"
                    risk_level   = "HIGH"
                else:
                    final_action = "QUARANTINE"
                    risk_level   = "MEDIUM"
            else:
                # Normal prediction
                if confidence_val >= 0.8:
                    final_action = "ALLOW"
                    risk_level   = "LOW"
                else:
                    final_action = "QUARANTINE"
                    risk_level   = "MEDIUM"

            # Build decision object
            decision = {
                "action": final_action,
                "confidence": float(binary_confidences[i]),
                "attack_type": attack_types[i],
                "prediction": prediction_label,
                "binary_pred": int(binary_preds[i]),
                "trust": {
                    "trust_score": round(computed_ts, 4),
                    "risk_level": risk_level
                },
                "attack_proba": attack_probas[i],
                "margin": float(margins[i])
            }
            final_decisions.append(decision)
            
            # Async Anomaly Feedback Logging (Non-blocking)
            if risk_level == "HIGH" or binary_preds[i] == 1:
                log_feedback_async({
                    "prediction": decision["prediction"],
                    "attack_type": decision["attack_type"],
                    "trust": decision["trust"],
                    "features": feature_vector.tolist()
                })
            
            # Per-flow audit logging
            logger.info(
                f"Prediction={prediction_label} | "
                f"Conf={confidence_val:.4f} | "
                f"Trust={computed_ts:.4f} | "
                f"Action={final_action}"
            )

        elapsed = time.time() - t0
        logger.info(
            "Processed %d flows in %.3fs  (%.1f flows/sec) — "
            "ALLOW=%d  QUARANTINE=%d  DENY=%d",
            len(df),
            elapsed,
            len(df) / elapsed if elapsed > 0 else float("inf"),
            sum(1 for d in final_decisions if d["action"] == "ALLOW"),
            sum(1 for d in final_decisions if d["action"] == "QUARANTINE"),
            sum(1 for d in final_decisions if d["action"] == "DENY"),
        )

        return final_decisions

    # ----------------------------------------------------------------
    # Results formatting
    # ----------------------------------------------------------------

    @staticmethod
    def to_dataframe(decisions: list[PolicyDecision]) -> pd.DataFrame:
        """
        Convert a list of PolicyDecisions to a tidy DataFrame.

        Useful for logging, dashboards, or writing results to CSV.

        Columns: action, binary_pred, confidence, attack_type,
                 timestamp, reason
        """
        rows = []
        for d in decisions:
            row = d.to_dict()
            row.pop("attack_proba", None)  # too wide for tabular display
            rows.append(row)
        return pd.DataFrame(rows)

    # ----------------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------------

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Align input DataFrame to the trained feature list.

        - Drops any columns not in the selected feature list
        - Fills missing selected features with 0.0 (with a warning)
        - Replaces Inf/NaN
        - Casts to float32
        """
        missing_cols = [f for f in self._features if f not in df.columns]
        if missing_cols:
            raise HTTPException(
                status_code=422,
                detail=f"Missing {len(missing_cols)} required features: {list(missing_cols)[:5]}..."
            )

        # Enforce exact feature ordering
        x = df[self._features].copy()
        
        x = x.replace([np.inf, -np.inf], np.nan)
        if x.isnull().values.any():
            raise HTTPException(status_code=422, detail="Invalid numeric values (inf/NaN) in payload")
            
        return x.astype(np.float32)


# ==================================================================
# Module-level convenience functions
# ==================================================================

_default_pipeline: Optional[InferencePipeline] = None


def _get_default_pipeline() -> InferencePipeline:
    """Return a cached default pipeline (loaded once per process)."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = InferencePipeline()
    return _default_pipeline


def predict(
    df: pd.DataFrame,
    binary_threshold: float = 0.3,
) -> list[PolicyDecision]:
    """
    Module-level convenience wrapper: predict on a DataFrame.

    Uses a process-scoped cached pipeline (artifacts loaded once).
    Pass *df* as a DataFrame of raw network flow features.

    Parameters
    ----------
    df : pd.DataFrame
        One row per network flow.
    binary_threshold : float
        Attack probability threshold (default 0.5).

    Returns
    -------
    list[PolicyDecision]
    """
    pipeline = _get_default_pipeline()
    pipeline._threshold = binary_threshold
    return pipeline.predict(df)


def predict_one(
    row: Union[dict, pd.Series],
    binary_threshold: float = 0.3,
) -> PolicyDecision:
    """
    Module-level convenience wrapper: predict a single flow.

    Parameters
    ----------
    row : dict | pd.Series
    binary_threshold : float

    Returns
    -------
    PolicyDecision
    """
    pipeline = _get_default_pipeline()
    pipeline._threshold = binary_threshold
    return pipeline.predict_one(row)


# ==================================================================
# CLI — smoke test / demo
# ==================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Inference Pipeline (Stage 7)"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to a CSV file of raw network flows to predict",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Binary attack probability threshold (default: 0.5)",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Save results to this CSV path"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Number of rows to print from results (default: 5)",
    )
    args = parser.parse_args()

    pipeline = InferencePipeline(binary_threshold=args.threshold)

    if args.csv:
        df_input = pd.read_csv(args.csv)
        logger.info("Loaded %d rows from %s", len(df_input), args.csv)
    else:
        # Demo: use a small slice from the processed test split
        logger.info("No CSV provided — loading sample rows from test split…")
        from src.features.preprocessor import load_splits

        x_test, _, _ = load_splits("test")
        df_input = x_test.head(20)

    decisions = pipeline.predict(df_input)

    print(f"\n{'=' * 60}")
    print("  Inference Results")
    print(f"{'=' * 60}")
    for i, d in enumerate(decisions[: args.sample]):
        print(f"  [{i + 1}] {d}")

    if args.output:
        result_df = InferencePipeline.to_dataframe(decisions)
        result_df.to_csv(args.output, index=False)
        print(f"\nResults saved → {args.output}")
