"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Multi-class Trainer (Stage 4)
Author: CyberSentinel ML-LAB

Trains an attack-type classifier that runs *after* the binary classifier.
Only attack-labelled samples (binary == 1) are used for training.

Pipeline:
    1. Load scaled train/val splits from Stage 2 parquet files
    2. Filter to attack-only rows (binary == 1)
    3. Encode attack-type string labels with LabelEncoder
    4. Apply class_weight='balanced' (multi-class SMOTE-NC is slow; optional)
    5. Train a RandomForest with per-class balanced weighting
    6. Evaluate on val set → macro/weighted F1, per-class report
    7. Save model.pkl + label_encoder.pkl to models/multiclass/
    8. Save metadata.json with metrics, classes, and feature list

Design note:
    Multi-class is intentionally trained ONLY on attack rows.
    At inference time:  binary=0 → ALLOW (skip multi-class)
                        binary=1 → run multi-class → get attack type

Outputs:
    models/multiclass/
        model.pkl
        label_encoder.pkl
        metadata.json
"""

from __future__ import annotations

import json
import logging
import time
import warnings
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder

from src.features.preprocessor import load_splits

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("multiclass_trainer")

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models" / "multiclass"
CONFIG_PATH = PROJECT_ROOT / "configs" / "training.yaml"
MODEL_FILENAME = "model.pkl"
ENCODER_FILENAME = "label_encoder.pkl"
MODEL_PATH = MODELS_DIR / MODEL_FILENAME
ENCODER_PATH = MODELS_DIR / ENCODER_FILENAME
METADATA_PATH = MODELS_DIR / "metadata.json"


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("multiclass_training", {})
    return {}


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _filter_attacks(
    x: pd.DataFrame,
    y_binary: pd.Series,
    y_label: pd.Series,
    split_name: str,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Keep only attack rows (binary == 1) and return (X, label series).

    BENIGN rows are excluded — multi-class is only responsible for
    identifying the *type* of attack after binary has flagged traffic.
    """
    mask = y_binary == 1
    x_attacks = x[mask].reset_index(drop=True)
    y_attacks = y_label[mask].reset_index(drop=True)

    # Drop any accidental 'BENIGN' / 'benign' rows still in the label column
    benign_mask = y_attacks.str.upper().str.strip() == "BENIGN"
    if benign_mask.any():
        logger.warning(
            "[%s] Found %d 'BENIGN' rows under binary==1 — dropping them.",
            split_name, benign_mask.sum(),
        )
        x_attacks = x_attacks[~benign_mask].reset_index(drop=True)
        y_attacks = y_attacks[~benign_mask].reset_index(drop=True)

    logger.info(
        "[%s] Attack rows: %d  |  Unique attack types: %d",
        split_name, len(x_attacks), y_attacks.nunique(),
    )
    return x_attacks, y_attacks


def _apply_smote_multiclass(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Apply SMOTE to multi-class attack labels.

    Classes with fewer than *min_class_samples* rows are skipped by SMOTE
    (not enough neighbours). Uses class_weight='balanced' instead when
    imbalanced-learn is unavailable.
    """
    try:
        from imblearn.over_sampling import SMOTE  # type: ignore

        # SMOTE requires k_neighbors < class_size; find safe k
        min_count = y_train.value_counts().min()
        k_neighbors = max(1, min(5, min_count - 1))

        smote = SMOTE(random_state=random_state, k_neighbors=k_neighbors, n_jobs=-1)
        x_res, y_res = smote.fit_resample(x_train, y_train)
        x_res = pd.DataFrame(x_res, columns=x_train.columns)
        y_res = pd.Series(y_res, name=y_train.name)
        logger.info(
            "SMOTE applied — train size: %d → %d",
            len(x_train), len(x_res),
        )
        return x_res, y_res
    except ImportError:
        warnings.warn(
            "imbalanced-learn not installed; falling back to class_weight='balanced'.",
            stacklevel=2,
        )
        logger.warning("SMOTE skipped — imbalanced-learn not available.")
        return x_train, y_train


def _evaluate_multiclass(
    model: RandomForestClassifier,
    encoder: LabelEncoder,
    x: pd.DataFrame,
    y_encoded: pd.Series,
    split_name: str,
) -> dict:
    """
    Evaluate multi-class model: macro/weighted F1, per-class report,
    confusion matrix over encoded class indices.
    """
    y_pred = model.predict(x)

    # Human-readable class names for the report
    class_names = encoder.classes_.tolist()
    report = classification_report(
        y_encoded, y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_encoded, y_pred).tolist()

    metrics = {
        "split": split_name,
        "accuracy": round(float(report["accuracy"]), 6),
        "f1_weighted": round(
            float(f1_score(y_encoded, y_pred, average="weighted", zero_division=0)), 6
        ),
        "f1_macro": round(
            float(f1_score(y_encoded, y_pred, average="macro", zero_division=0)), 6
        ),
        "precision_weighted": round(
            float(precision_score(y_encoded, y_pred, average="weighted", zero_division=0)), 6
        ),
        "recall_weighted": round(
            float(recall_score(y_encoded, y_pred, average="weighted", zero_division=0)), 6
        ),
        "confusion_matrix": cm,
        "classification_report": report,
    }

    logger.info(
        "[%s] Accuracy=%.4f  F1(weighted)=%.4f  F1(macro)=%.4f",
        split_name.upper(),
        metrics["accuracy"],
        metrics["f1_weighted"],
        metrics["f1_macro"],
    )
    return metrics


# ------------------------------------------------------------------
# Public trainer
# ------------------------------------------------------------------

def train_multiclass_classifier(
    use_smote: Optional[bool] = None,
    n_estimators: Optional[int] = None,
    max_depth: Optional[int] = None,
    min_samples_leaf: Optional[int] = None,
    max_features: Optional[str] = None,
    random_state: Optional[int] = None,
    n_jobs: int = -1,
    model_dir: Optional[Path] = None,
) -> tuple[RandomForestClassifier, LabelEncoder]:
    """
    Train and save the multi-class attack-type classifier.

    Must be run *after* Stage 2 (preprocessor), as it reads parquet splits.
    All parameters fall back to ``configs/training.yaml`` →
    ``multiclass_training`` section, then to sensible hardcoded defaults.

    Parameters
    ----------
    use_smote : bool, optional
        Apply SMOTE on the attack-only training subset (default True).
    n_estimators : int, optional
        Number of trees (default 300).
    max_depth : int | None, optional
        Max tree depth; None = unlimited (default None).
    min_samples_leaf : int, optional
        Min samples per leaf (default 4).
    max_features : str, optional
        Feature subset per split (default 'sqrt').
    random_state : int, optional
        Seed (default 42).
    n_jobs : int
        Parallelism (-1 = all cores).
    model_dir : Path, optional
        Override save directory (default models/multiclass/).

    Returns
    -------
    tuple[RandomForestClassifier, LabelEncoder]
        The fitted model and the label encoder used for attack classes.
    """
    t0 = time.time()
    cfg = _load_config()

    # Resolve params (caller > config > default)
    use_smote = use_smote if use_smote is not None else cfg.get("use_smote", True)
    n_estimators = n_estimators if n_estimators is not None else cfg.get("n_estimators", 300)
    max_depth = max_depth if max_depth is not None else cfg.get("max_depth", None)
    min_samples_leaf = min_samples_leaf if min_samples_leaf is not None \
        else cfg.get("min_samples_leaf", 4)
    max_features = max_features if max_features is not None else cfg.get("max_features", "sqrt")
    random_state = random_state if random_state is not None else cfg.get("random_state", 42)
    model_dir = model_dir or MODELS_DIR
    model_dir.mkdir(parents=True, exist_ok=True)

    # ---- load Stage 2 splits ------------------------------------------
    logger.info("Loading train split…")
    x_train_full, y_train_binary, y_train_label = load_splits("train")
    logger.info("Loading val split…")
    x_val_full, y_val_binary, y_val_label = load_splits("val")

    feature_names = x_train_full.columns.tolist()

    # ---- filter to attack rows only -----------------------------------
    x_train, y_train_raw = _filter_attacks(x_train_full, y_train_binary, y_train_label, "train")
    x_val, y_val_raw = _filter_attacks(x_val_full, y_val_binary, y_val_label, "val")

    if len(x_train) == 0:
        raise ValueError(
            "No attack rows found in the training split. "
            "Ensure Stage 2 preprocessing has run and 'binary' column is populated correctly."
        )

    logger.info(
        "Train attack rows: %d  |  Val attack rows: %d  |  Features: %d",
        len(x_train), len(x_val), len(feature_names),
    )

    # ---- encode labels ------------------------------------------------
    encoder = LabelEncoder()
    # Fit on train labels only, but handle val labels that might be unseen
    encoder.fit(y_train_raw)
    attack_classes = encoder.classes_.tolist()
    logger.info("Attack classes (%d): %s", len(attack_classes), attack_classes)

    y_train_enc = pd.Series(encoder.transform(y_train_raw), name="attack_type")

    # Remap val labels: unseen classes → -1 (edge case for rare attack types)
    known = set(attack_classes)
    val_known_mask = y_val_raw.isin(known)
    unseen_count = (~val_known_mask).sum()
    if unseen_count > 0:
        logger.warning(
            "%d val rows have unseen attack types not in train — they will be excluded from eval.",
            unseen_count,
        )
    x_val = x_val[val_known_mask].reset_index(drop=True)
    y_val_enc = pd.Series(
        encoder.transform(y_val_raw[val_known_mask].reset_index(drop=True)),
        name="attack_type",
    )

    logger.info("Train class distribution:\n%s", y_train_raw.value_counts().to_string())

    # ---- class-imbalance handling ------------------------------------
    if use_smote:
        x_train, y_train_enc = _apply_smote_multiclass(x_train, y_train_enc, random_state)
        class_weight_param = None
    else:
        class_weight_param = "balanced"
        logger.info("Using class_weight='balanced' instead of SMOTE.")

    # ---- build and train model ----------------------------------------
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        class_weight=class_weight_param,
        random_state=random_state,
        n_jobs=n_jobs,
        verbose=0,
    )

    logger.info(
        "Training RandomForest (multi-class) — n_estimators=%d  max_depth=%s  "
        "min_samples_leaf=%d  max_features=%s  class_weight=%s",
        n_estimators, max_depth, min_samples_leaf, max_features,
        class_weight_param if not use_smote else "none (SMOTE used)",
    )

    model.fit(x_train, y_train_enc)
    train_elapsed = time.time() - t0
    logger.info("Training complete in %.1fs", train_elapsed)

    # ---- evaluate on val set ------------------------------------------
    val_metrics = _evaluate_multiclass(model, encoder, x_val, y_val_enc, "val")

    # ---- save model + encoder -----------------------------------------
    model_path = model_dir / MODEL_FILENAME
    encoder_path = model_dir / ENCODER_FILENAME
    joblib.dump(model, model_path)
    joblib.dump(encoder, encoder_path)
    logger.info("Saved model → %s", model_path)
    logger.info("Saved encoder → %s", encoder_path)

    # ---- feature importance -------------------------------------------
    importance_series = (
        pd.Series(model.feature_importances_, index=feature_names)
        .sort_values(ascending=False)
    )
    top_20_importances = importance_series.head(20).to_dict()

    # ---- save metadata ------------------------------------------------
    elapsed = time.time() - t0
    metadata = {
        "model_type": "RandomForestClassifier",
        "task": "multiclass_attack_classification",
        "attack_classes": attack_classes,
        "num_classes": len(attack_classes),
        "training_config": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
            "max_features": max_features,
            "class_weight": "balanced" if not use_smote else None,
            "use_smote": use_smote,
            "random_state": random_state,
        },
        "data": {
            "train_attack_rows": int(len(x_train)),
            "val_attack_rows": int(len(x_val)),
            "feature_count": int(len(feature_names)),
            "features": feature_names,
            "note": "Only attack rows (binary==1) used; benign excluded by design.",
        },
        "val_metrics": val_metrics,
        "top_20_feature_importances": {
            k: round(float(v), 8) for k, v in top_20_importances.items()
        },
        "model_path": str(model_path),
        "encoder_path": str(encoder_path),
        "elapsed_seconds": round(elapsed, 2),
    }

    metadata_path = model_dir / "metadata.json"
    with open(metadata_path, "w") as fh:
        json.dump(metadata, fh, indent=2)
    logger.info("Saved metadata → %s", metadata_path)

    # ---- print summary -------------------------------------------------
    print("\n" + "=" * 60)
    print("  Multi-class Classifier — Training Summary")
    print("=" * 60)
    print(f"  Model          : RandomForestClassifier ({n_estimators} trees)")
    print(f"  Features       : {len(feature_names)}")
    print(f"  Attack classes : {len(attack_classes)}")
    print(f"  Train rows     : {len(x_train):,}  (attack only)")
    print(f"  Val rows       : {len(x_val):,}  (attack only)")
    print(f"  Imbalance      : {'SMOTE' if use_smote else 'class_weight=balanced'}")
    print(f"  Val Accuracy   : {val_metrics['accuracy']:.4f}")
    print(f"  Val F1 (w)     : {val_metrics['f1_weighted']:.4f}")
    print(f"  Val F1 (macro) : {val_metrics['f1_macro']:.4f}")
    print(f"  Elapsed        : {elapsed:.1f}s")
    print("=" * 60)
    print("\n  Attack classes:")
    for cls in attack_classes:
        print(f"    • {cls}")

    return model, encoder


# ------------------------------------------------------------------
# Loaders (used by inference pipeline)
# ------------------------------------------------------------------

def load_multiclass_model(
    model_dir: Optional[Path] = None,
) -> tuple[RandomForestClassifier, LabelEncoder]:
    """
    Load the saved multi-class classifier and its label encoder.

    Parameters
    ----------
    model_dir : Path, optional
        Directory containing model.pkl and label_encoder.pkl.
        Defaults to models/multiclass/.

    Returns
    -------
    tuple[RandomForestClassifier, LabelEncoder]
    """
    model_dir = model_dir or MODELS_DIR
    model_path = model_dir / MODEL_FILENAME
    encoder_path = model_dir / ENCODER_FILENAME

    for path, label in ((model_path, "model"), (encoder_path, "label encoder")):
        if not path.exists():
            raise FileNotFoundError(
                f"Multi-class {label} not found at '{path}'. "
                "Run `train_multiclass_classifier()` first."
            )

    model = joblib.load(model_path)
    encoder = joblib.load(encoder_path)
    logger.info("Loaded multi-class model + encoder from: %s", model_dir)
    return model, encoder


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Multi-class Classifier Training (Stage 4)"
    )
    parser.add_argument("--no-smote", action="store_true",
                        help="Disable SMOTE; use class_weight='balanced' instead")
    parser.add_argument("--n-estimators", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--min-samples-leaf", type=int, default=None)
    parser.add_argument("--max-features", type=str, default=None)
    parser.add_argument("--random-state", type=int, default=None)
    args = parser.parse_args()

    train_multiclass_classifier(
        use_smote=not args.no_smote,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        max_features=args.max_features,
        random_state=args.random_state,
    )
