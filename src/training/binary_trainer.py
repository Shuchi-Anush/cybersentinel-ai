"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Binary Trainer (Stage 3)
Author: CyberSentinel ML-LAB

Trains a binary classifier — Benign (0) vs Attack (1).

Pipeline:
    1. Load scaled train/val splits from Stage 2 parquet files
    2. Optionally over-sample the minority class with SMOTE
    3. Train a RandomForest baseline (class_weight='balanced' fallback)
    4. Evaluate on val set → classification report, ROC-AUC, F1
    5. Save model to models/binary/model.pkl
    6. Save metadata.json with metrics, config, and feature list

Outputs:
    models/binary/
        model.pkl
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
    roc_auc_score,
)

from src.features.preprocessor import load_splits

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("binary_trainer")

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models" / "binary"
CONFIG_PATH = PROJECT_ROOT / "configs" / "training.yaml"
MODEL_FILENAME = "model.pkl"
MODEL_PATH = MODELS_DIR / MODEL_FILENAME
METADATA_PATH = MODELS_DIR / "metadata.json"


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("binary_training", {})
    return {}


# ------------------------------------------------------------------
# Class-imbalance handling
# ------------------------------------------------------------------

def _apply_smote(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Over-sample the minority class with SMOTE.

    Falls back gracefully to class_weight='balanced' when imbalanced-learn
    is not installed — logs a warning so the caller knows.
    """
    try:
        from imblearn.over_sampling import SMOTE  # type: ignore
        smote = SMOTE(random_state=random_state, n_jobs=-1)
        x_res, y_res = smote.fit_resample(x_train, y_train)
        x_res = pd.DataFrame(x_res, columns=x_train.columns)
        y_res = pd.Series(y_res, name=y_train.name)
        logger.info(
            "SMOTE applied — train size: %d → %d  |  class dist: %s",
            len(x_train), len(x_res), dict(y_res.value_counts()),
        )
        return x_res, y_res
    except ImportError:
        warnings.warn(
            "imbalanced-learn not installed; falling back to class_weight='balanced'. "
            "Install with: pip install imbalanced-learn",
            stacklevel=2,
        )
        logger.warning("SMOTE skipped — imbalanced-learn not available.")
        return x_train, y_train


# ------------------------------------------------------------------
# Evaluation helper
# ------------------------------------------------------------------

def _evaluate(
    model: RandomForestClassifier,
    x: pd.DataFrame,
    y: pd.Series,
    split_name: str,
) -> dict:
    """Run predict / predict_proba and compute all standard metrics."""
    y_pred = model.predict(x)
    y_proba = model.predict_proba(x)[:, 1]

    report = classification_report(y, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, y_pred).tolist()

    metrics = {
        "split": split_name,
        "accuracy": round(float(report["accuracy"]), 6),
        "f1_weighted": round(float(f1_score(y, y_pred, average="weighted", zero_division=0)), 6),
        "f1_macro": round(float(f1_score(y, y_pred, average="macro", zero_division=0)), 6),
        "precision_weighted": round(
            float(precision_score(y, y_pred, average="weighted", zero_division=0)), 6
        ),
        "recall_weighted": round(
            float(recall_score(y, y_pred, average="weighted", zero_division=0)), 6
        ),
        "roc_auc": round(float(roc_auc_score(y, y_proba)), 6),
        "confusion_matrix": cm,
        "classification_report": report,
    }

    logger.info(
        "[%s] Accuracy=%.4f  F1(weighted)=%.4f  ROC-AUC=%.4f",
        split_name.upper(),
        metrics["accuracy"],
        metrics["f1_weighted"],
        metrics["roc_auc"],
    )
    return metrics


# ------------------------------------------------------------------
# Public trainer
# ------------------------------------------------------------------

def train_binary_classifier(
    use_smote: Optional[bool] = None,
    n_estimators: Optional[int] = None,
    max_depth: Optional[int] = None,
    min_samples_leaf: Optional[int] = None,
    max_features: Optional[str] = None,
    random_state: Optional[int] = None,
    n_jobs: int = -1,
    model_dir: Optional[Path] = None,
) -> RandomForestClassifier:
    """
    Train and save the binary intrusion-detection classifier.

    All parameters fall back to ``configs/training.yaml`` → ``binary_training``
    section, then to sensible hardcoded defaults.

    Parameters
    ----------
    use_smote : bool, optional
        Whether to apply SMOTE before training (default True).
    n_estimators : int, optional
        Number of trees (default 300).
    max_depth : int | None, optional
        Max tree depth; None = unlimited (default None).
    min_samples_leaf : int, optional
        Min samples per leaf (default 4).
    max_features : str, optional
        Feature subset strategy per split (default 'sqrt').
    random_state : int, optional
        Seed (default 42).
    n_jobs : int
        Parallelism; -1 = all cores.
    model_dir : Path, optional
        Override save directory (default models/binary/).

    Returns
    -------
    RandomForestClassifier
        The fitted model.
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

    # ---- load splits from Stage 2 -----------------------------------
    logger.info("Loading train split…")
    x_train, y_train_binary, _ = load_splits("train")
    logger.info("Loading val split…")
    x_val, y_val_binary, _ = load_splits("val")

    feature_names = x_train.columns.tolist()
    logger.info(
        "Train: %d rows  |  Val: %d rows  |  Features: %d",
        len(x_train), len(x_val), len(feature_names),
    )
    logger.info("Train class distribution: %s", dict(y_train_binary.value_counts()))

    # ---- class-imbalance handling -----------------------------------
    if use_smote:
        x_train, y_train_binary = _apply_smote(x_train, y_train_binary, random_state)
        class_weight_param = None          # SMOTE handles balance
    else:
        class_weight_param = "balanced"    # Let RF handle it natively
        logger.info("Using class_weight='balanced' instead of SMOTE.")

    # ---- build and train the model ----------------------------------
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
        "Training RandomForest — n_estimators=%d  max_depth=%s  "
        "min_samples_leaf=%d  max_features=%s  class_weight=%s",
        n_estimators, max_depth, min_samples_leaf, max_features,
        class_weight_param if not use_smote else "none (SMOTE used)",
    )

    model.fit(x_train, y_train_binary)
    logger.info("Training complete in %.1fs", time.time() - t0)

    # ---- evaluate on val set ----------------------------------------
    val_metrics = _evaluate(model, x_val, y_val_binary, "val")

    # ---- save model -------------------------------------------------
    model_path = model_dir / MODEL_FILENAME
    joblib.dump(model, model_path)
    logger.info("Saved model → %s", model_path)

    # ---- build feature importance table -----------------------------
    importance_df = (
        pd.Series(model.feature_importances_, index=feature_names)
        .sort_values(ascending=False)
    )
    top_20_importances = importance_df.head(20).to_dict()

    # ---- save metadata ----------------------------------------------
    elapsed = time.time() - t0
    metadata = {
        "model_type": "RandomForestClassifier",
        "task": "binary_classification",
        "classes": {0: "Benign", 1: "Attack"},
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
            "train_rows": int(len(x_train)),
            "val_rows": int(len(x_val)),
            "feature_count": int(len(feature_names)),
            "features": feature_names,
        },
        "val_metrics": val_metrics,
        "top_20_feature_importances": {
            k: round(float(v), 8) for k, v in top_20_importances.items()
        },
        "model_path": str(model_path),
        "elapsed_seconds": round(elapsed, 2),
    }

    metadata_path = model_dir / "metadata.json"
    with open(metadata_path, "w") as fh:
        json.dump(metadata, fh, indent=2)
    logger.info("Saved metadata → %s", metadata_path)

    # ---- print summary ----------------------------------------------
    print("\n" + "=" * 55)
    print("  Binary Classifier — Training Summary")
    print("=" * 55)
    print(f"  Model        : RandomForestClassifier ({n_estimators} trees)")
    print(f"  Features     : {len(feature_names)}")
    print(f"  Train rows   : {len(x_train):,}")
    print(f"  Val rows     : {len(x_val):,}")
    print(f"  Imbalance    : {'SMOTE' if use_smote else 'class_weight=balanced'}")
    print(f"  Val Accuracy : {val_metrics['accuracy']:.4f}")
    print(f"  Val F1 (w)   : {val_metrics['f1_weighted']:.4f}")
    print(f"  Val ROC-AUC  : {val_metrics['roc_auc']:.4f}")
    print(f"  Elapsed      : {elapsed:.1f}s")
    print("=" * 55)

    return model


# ------------------------------------------------------------------
# Model loader (used by inference + Stage 4 multi-class pipeline)
# ------------------------------------------------------------------

def load_binary_model(model_dir: Optional[Path] = None) -> RandomForestClassifier:
    """
    Load the saved binary classifier from disk.

    Parameters
    ----------
    model_dir : Path, optional
        Directory containing model.pkl.  Defaults to models/binary/.

    Returns
    -------
    RandomForestClassifier
    """
    model_dir = model_dir or MODELS_DIR
    path = model_dir / MODEL_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Binary model not found at '{path}'. "
            "Run `train_binary_classifier()` first."
        )
    model = joblib.load(path)
    logger.info("Loaded binary model from: %s", path)
    return model


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Binary Classifier Training (Stage 3)"
    )
    parser.add_argument("--no-smote", action="store_true",
                        help="Disable SMOTE; use class_weight='balanced' instead")
    parser.add_argument("--n-estimators", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--min-samples-leaf", type=int, default=None)
    parser.add_argument("--max-features", type=str, default=None)
    parser.add_argument("--random-state", type=int, default=None)
    args = parser.parse_args()

    train_binary_classifier(
        use_smote=not args.no_smote,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        max_features=args.max_features,
        random_state=args.random_state,
    )
