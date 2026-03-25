"""
CyberSentinel AI — features package

Public API
----------
    from src.features import run_feature_selection, load_selected_features
    from src.features import run_preprocessing, load_splits, load_scaler
"""

from src.features.selector import (
    run_feature_selection,
    load_selected_features,
    apply_variance_threshold,
    apply_correlation_filter,
    apply_select_k_best,
    apply_tree_importance,
)
from src.features.preprocessor import (
    run_preprocessing,
    load_splits,
    load_scaler,
)

__all__ = [
    # Stage 1 — Feature Selection
    "run_feature_selection",
    "load_selected_features",
    "apply_variance_threshold",
    "apply_correlation_filter",
    "apply_select_k_best",
    "apply_tree_importance",
    # Stage 2 — Preprocessing
    "run_preprocessing",
    "load_splits",
    "load_scaler",
]

