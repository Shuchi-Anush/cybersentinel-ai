"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Feature Selection Module (Stage 1)
Author: CyberSentinel ML-LAB

Runs four complementary selection methods in sequence:
    1. Variance Threshold   — drops near-zero variance features
    2. Correlation Filter   — removes one of each highly-correlated pair
    3. SelectKBest (ANOVA-F)— keeps top-K features by F-score vs binary label
    4. Tree-Based Importance— ranks remaining features by RandomForest importance

Saves results to: configs/selected_features.json
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif

import yaml
from src.core.paths import CONFIGS_DIR

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("selector")


# ------------------------------------------------------------------
# Path configuration (mirrors train_pipeline.py convention)
# ------------------------------------------------------------------

from src.core.paths import DATA_DIR

PROCESSED_DIR = DATA_DIR / "processed"

CONFIG_PATH = CONFIGS_DIR / "training.yaml"
OUTPUT_PATH = CONFIGS_DIR / "selected_features.json"


# ------------------------------------------------------------------
# Config loader
# ------------------------------------------------------------------


def _load_config() -> dict:
    """Load training.yaml; return an empty dict if not found."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("feature_selection", {})
    return {}


# ------------------------------------------------------------------
# Private helpers (reduce cognitive complexity of orchestrator)
# ------------------------------------------------------------------


def _resolve_params(
    cfg: dict,
    data_path: Optional[Path],
    output_path: Optional[Path],
    variance_threshold: Optional[float],
    correlation_threshold: Optional[float],
    kbest_k: Optional[int],
    tree_top_n: Optional[int],
) -> tuple:
    """Merge caller-supplied overrides with config / hardcoded defaults."""
    data_path = data_path or (PROCESSED_DIR / "merged_cleaned.csv")
    output_path = output_path or OUTPUT_PATH
    variance_threshold = (
        variance_threshold
        if variance_threshold is not None
        else cfg.get("variance_threshold", 0.01)
    )
    correlation_threshold = (
        correlation_threshold
        if correlation_threshold is not None
        else cfg.get("correlation_threshold", 0.95)
    )
    kbest_k = kbest_k if kbest_k is not None else cfg.get("kbest_k", 40)
    tree_top_n = tree_top_n if tree_top_n is not None else cfg.get("tree_top_n", 40)
    return (
        data_path,
        output_path,
        variance_threshold,
        correlation_threshold,
        kbest_k,
        tree_top_n,
    )


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure 'label' and 'binary' columns exist.

    Tries title-cased variants ('Label', 'Binary') and renames in place.
    Raises ValueError if neither variant exists.
    """
    rename_map = {}
    for col in ("label", "binary"):
        if col not in df.columns:
            title_col = col.title()
            if title_col in df.columns:
                rename_map[title_col] = col
    if rename_map:
        df = df.rename(columns=rename_map)
    missing = [c for c in ("label", "binary") if c not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset missing required columns: {missing}. "
            f"Available columns: {df.columns.tolist()[:20]}…"
        )
    return df


def _clean_features(x: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Drop non-numeric columns and replace Inf/NaN values.

    Returns the cleaned DataFrame and the original feature count.
    """
    initial_features = x.shape[1]
    logger.info("Feature matrix shape: %s", x.shape)
    non_numeric = x.select_dtypes(exclude=[np.number]).columns.tolist()
    if non_numeric:
        logger.warning(
            "Dropping %d non-numeric columns: %s", len(non_numeric), non_numeric
        )
        x = x.drop(columns=non_numeric)
    x = x.replace([np.inf, -np.inf], np.nan)
    x = x.fillna(x.median(numeric_only=True))
    return x, initial_features


# ------------------------------------------------------------------
# Step 1 — Variance Threshold
# ------------------------------------------------------------------


def apply_variance_threshold(
    X: pd.DataFrame,
    threshold: float = 0.01,
) -> pd.DataFrame:
    """
    Drop features whose variance is below *threshold*.

    Parameters
    ----------
    X : pd.DataFrame
        Feature matrix (no label columns).
    threshold : float
        Features with variance <= threshold are removed.

    Returns
    -------
    pd.DataFrame
        Reduced feature matrix.
    """
    before = X.shape[1]
    selector = VarianceThreshold(threshold=threshold)
    selector.fit(X)
    mask = selector.get_support()
    x_out = X.loc[:, mask]
    dropped = before - x_out.shape[1]
    logger.info(
        "Variance Threshold (th=%.4f): %d → %d features  (dropped %d)",
        threshold,
        before,
        x_out.shape[1],
        dropped,
    )
    return x_out


# ------------------------------------------------------------------
# Step 2 — Correlation Filter
# ------------------------------------------------------------------


def apply_correlation_filter(
    X: pd.DataFrame,
    threshold: float = 0.95,
) -> pd.DataFrame:
    """
    Remove one feature from each pair whose Pearson correlation exceeds
    *threshold*. The feature with the lower mean absolute correlation is
    kept (greedy, upper-triangle approach).

    Parameters
    ----------
    X : pd.DataFrame
    threshold : float
        Pairs with |r| >= threshold → drop the second feature.

    Returns
    -------
    pd.DataFrame
        Reduced feature matrix.
    """
    before = X.shape[1]
    corr_matrix = X.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] >= threshold)]
    x_out = X.drop(columns=to_drop)
    logger.info(
        "Correlation Filter (th=%.2f): %d → %d features  (dropped %d)",
        threshold,
        before,
        x_out.shape[1],
        before - x_out.shape[1],
    )
    return x_out


# ------------------------------------------------------------------
# Step 3 — SelectKBest (ANOVA-F vs binary label)
# ------------------------------------------------------------------


def apply_select_k_best(
    X: pd.DataFrame,
    y_binary: pd.Series,
    k: int = 40,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """
    Keep the top *k* features ranked by ANOVA-F score against the binary
    target (0 = Benign, 1 = Attack).

    Parameters
    ----------
    X : pd.DataFrame
    y_binary : pd.Series
        Binary label column.
    k : int
        Number of features to keep.  Clamped to X.shape[1] automatically.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, float]]
        Reduced DataFrame and a dict mapping feature name → F-score.
    """
    k = min(k, X.shape[1])
    before = X.shape[1]
    selector = SelectKBest(score_func=f_classif, k=k)
    selector.fit(X, y_binary)
    mask = selector.get_support()
    scores = dict(zip(X.columns[mask], selector.scores_[mask]))
    x_out = X.loc[:, mask]
    logger.info(
        "SelectKBest (k=%d): %d → %d features",
        k,
        before,
        x_out.shape[1],
    )
    return x_out, scores


# ------------------------------------------------------------------
# Step 4 — Tree-Based Feature Importance
# ------------------------------------------------------------------


def apply_tree_importance(
    X: pd.DataFrame,
    y_binary: pd.Series,
    top_n: int = 40,
    random_state: int = 42,
    n_jobs: int = -1,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """
    Rank features by importance from an ensemble of ExtraTrees + RandomForest,
    averaged across both estimators. Keeps the top *top_n* features.

    Uses ExtraTrees for speed on large datasets; RandomForest for robustness.
    Both are fitted on a stratified sample (max 200 000 rows) to keep runtime
    reasonable without sacrificing representativeness.

    Parameters
    ----------
    X : pd.DataFrame
    y_binary : pd.Series
    top_n : int
        How many features to keep after ranking.
    random_state : int
    n_jobs : int
        Parallelism; -1 = use all cores.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, float]]
        Reduced DataFrame and importance dict {feature: averaged_importance}.
    """
    before = X.shape[1]

    # Stratified sample to keep wall-clock time manageable
    MAX_ROWS = 200_000
    if len(X) > MAX_ROWS:
        sample_idx = pd.concat(
            [
                y_binary[y_binary == 0].sample(
                    MAX_ROWS // 2, random_state=random_state
                ),
                y_binary[y_binary == 1].sample(
                    MAX_ROWS // 2, random_state=random_state
                ),
            ]
        ).index
        x_sample = X.loc[sample_idx]
        y_sample = y_binary.loc[sample_idx]
    else:
        x_sample, y_sample = X, y_binary

    et = ExtraTreesClassifier(
        n_estimators=100,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=random_state,
        n_jobs=n_jobs,
    )
    rf = RandomForestClassifier(
        n_estimators=100,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=random_state,
        n_jobs=n_jobs,
    )

    logger.info("Fitting ExtraTrees for importance ranking…")
    et.fit(x_sample, y_sample)
    logger.info("Fitting RandomForest for importance ranking…")
    rf.fit(x_sample, y_sample)

    importances = (et.feature_importances_ + rf.feature_importances_) / 2.0
    importance_series = pd.Series(importances, index=X.columns).sort_values(
        ascending=False
    )

    top_features = importance_series.head(top_n).index.tolist()
    importance_dict = importance_series.head(top_n).to_dict()

    x_out = X[top_features]
    logger.info(
        "Tree Importance (top_n=%d): %d → %d features",
        top_n,
        before,
        x_out.shape[1],
    )
    return x_out, importance_dict


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------


def run_feature_selection(
    data_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    variance_threshold: Optional[float] = None,
    correlation_threshold: Optional[float] = None,
    kbest_k: Optional[int] = None,
    tree_top_n: Optional[int] = None,
    random_state: int = 42,
    sample_for_corr: int = 100_000,
) -> list[str]:
    """
    Full feature selection pipeline.

    Loads ``merged_cleaned.csv`` (or *data_path*), runs all four selection
    steps in sequence, and writes ``selected_features.json`` to
    ``configs/``.

    Parameters
    ----------
    data_path : Path, optional
        Override default path to merged_cleaned.csv.
    output_path : Path, optional
        Override default output JSON path.
    variance_threshold : float, optional
        Overrides config / default (0.01).
    correlation_threshold : float, optional
        Overrides config / default (0.95).
    kbest_k : int, optional
        Overrides config / default (40).
    tree_top_n : int, optional
        Overrides config / default (40).
    random_state : int
        Global random seed.
    sample_for_corr : int
        Row sample used for the correlation matrix (expensive on full dataset).

    Returns
    -------
    list[str]
        Final selected feature names.
    """

    t0 = time.time()
    cfg = _load_config()
    (
        data_path,
        output_path,
        variance_threshold,
        correlation_threshold,
        kbest_k,
        tree_top_n,
    ) = _resolve_params(
        cfg,
        data_path,
        output_path,
        variance_threshold,
        correlation_threshold,
        kbest_k,
        tree_top_n,
    )

    # ---- load & validate data -------------------------------------------
    logger.info("Loading dataset from: %s", data_path)
    df = pd.read_csv(data_path, low_memory=False)
    logger.info("Dataset shape: %s", df.shape)
    df = _normalise_columns(df)

    label_cols = [c for c in df.columns if c in ("label", "binary", "Label", "Binary")]
    x_full = df.drop(columns=label_cols)
    y_binary = df["binary"].astype(int)
    x_full, initial_features = _clean_features(x_full)

    logger.info("Starting feature selection with %d features…", initial_features)

    # ---- Step 1: Variance Threshold -------------------------------------
    x_full = apply_variance_threshold(x_full, threshold=variance_threshold)

    # ---- Step 2: Correlation Filter (on sample for large datasets) ------
    if len(x_full) > sample_for_corr:
        logger.info("Using %d-row sample for correlation computation…", sample_for_corr)
        x_corr_sample = x_full.sample(sample_for_corr, random_state=random_state)
        corr_matrix = x_corr_sample.corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [
            col for col in upper.columns if any(upper[col] >= correlation_threshold)
        ]
        x_full = x_full.drop(columns=to_drop)
        logger.info(
            "Correlation Filter (th=%.2f): dropped %d features → %d remaining",
            correlation_threshold,
            len(to_drop),
            x_full.shape[1],
        )
    else:
        x_full = apply_correlation_filter(x_full, threshold=correlation_threshold)

    # ---- Step 3: SelectKBest -------------------------------------------
    x_full, kbest_scores = apply_select_k_best(x_full, y_binary, k=kbest_k)

    # ---- Step 4: Tree Importance ----------------------------------------
    x_full, tree_importances = apply_tree_importance(
        x_full, y_binary, top_n=tree_top_n, random_state=random_state
    )

    selected_features = x_full.columns.tolist()
    elapsed = time.time() - t0

    logger.info(
        "Feature selection complete: %d → %d features in %.1fs",
        initial_features,
        len(selected_features),
        elapsed,
    )

    # ---- Save results ---------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": {
            "source_dataset": str(data_path.name),
            "initial_features": initial_features,
            "selected_count": len(selected_features),
            "elapsed_seconds": round(elapsed, 2),
            "config": {
                "variance_threshold": variance_threshold,
                "correlation_threshold": correlation_threshold,
                "kbest_k": kbest_k,
                "tree_top_n": tree_top_n,
                "random_state": random_state,
            },
        },
        "selected_features": selected_features,
        "kbest_scores": {k: round(v, 6) for k, v in kbest_scores.items()},
        "tree_importances": {k: round(v, 8) for k, v in tree_importances.items()},
    }

    with open(output_path, "w") as fh:
        json.dump(payload, fh, indent=2)

    logger.info("Saved selected features → %s", output_path)

    return selected_features


# ------------------------------------------------------------------
# Loader utility (used at inference / training time)
# ------------------------------------------------------------------


def load_selected_features(path: Optional[Path] = None) -> list[str]:
    """
    Load the previously saved feature list from *selected_features.json*.

    Parameters
    ----------
    path : Path, optional
        Override default path.

    Returns
    -------
    list[str]
        Feature names in selection order.

    Raises
    ------
    FileNotFoundError
        If the JSON file does not exist yet (run ``run_feature_selection`` first).
    """
    path = path or OUTPUT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Feature list not found at '{path}'.  Run `run_feature_selection()` first."
        )
    with open(path, "r") as fh:
        data = json.load(fh)
    features = data["selected_features"]
    logger.info("Loaded %d selected features from: %s", len(features), path)
    return features


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Feature Selection (Stage 1)"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="Path to merged_cleaned.csv  [default: data/processed/merged_cleaned.csv]",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path  [default: configs/selected_features.json]",
    )
    parser.add_argument("--variance-threshold", type=float, default=None)
    parser.add_argument("--correlation-threshold", type=float, default=None)
    parser.add_argument("--kbest-k", type=int, default=None)
    parser.add_argument("--tree-top-n", type=int, default=None)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    features = run_feature_selection(
        data_path=args.data,
        output_path=args.output,
        variance_threshold=args.variance_threshold,
        correlation_threshold=args.correlation_threshold,
        kbest_k=args.kbest_k,
        tree_top_n=args.tree_top_n,
        random_state=args.random_state,
    )

    print(f"\nSelected {len(features)} features:")
    for f in features:
        print(f"  {f}")
