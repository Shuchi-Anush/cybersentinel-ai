"""
CyberSentinel AI — MetaService
Author: CyberSentinel ML-LAB

Loads all metadata JSON/YAML files once at startup and caches them
as plain dicts.  Zero disk I/O after initialisation.

This service NEVER loads .pkl models or runs inference.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import yaml

from src.core.paths import MODELS_DIR, CONFIGS_DIR, EVAL_DIR

logger = logging.getLogger("meta_service")


class MetaService:
    """
    Read-only metadata cache for the /meta/* API endpoints.

    Instantiated once during the FastAPI lifespan event.
    All public methods return plain dicts ready for JSON serialisation.
    """

    def __init__(self) -> None:
        logger.info("MetaService: loading metadata files…")

        # ---- load sources ------------------------------------------------
        self._binary_meta = self._load_json(MODELS_DIR / "binary" / "metadata.json")
        self._multiclass_meta = self._load_json(
            MODELS_DIR / "multiclass" / "metadata.json"
        )
        self._preprocessing = self._load_json(
            MODELS_DIR / "preprocessing_metadata.json"
        )
        self._policy = self._load_yaml(CONFIGS_DIR / "policy.yaml")
        self._training_config = self._load_yaml(CONFIGS_DIR / "training.yaml")
        self._eval_summary = self._load_json_optional(EVAL_DIR / "summary.json")

        logger.info("MetaService: all metadata loaded and cached.")

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def get_features(self) -> dict:
        """Feature list + top-20 importances for binary and multiclass."""
        return {
            "feature_count": self._binary_meta.get("data", {}).get("feature_count", 0),
            "features": self._binary_meta.get("data", {}).get("features", []),
            "binary_importances": self._binary_meta.get(
                "top_20_feature_importances", {}
            ),
            "multiclass_importances": self._multiclass_meta.get(
                "top_20_feature_importances", {}
            ),
        }

    def get_models(self) -> dict:
        """Model metadata for binary, multiclass, and preprocessing."""
        return {
            "binary": {
                "model_type": self._binary_meta.get("model_type"),
                "task": self._binary_meta.get("task"),
                "classes": self._binary_meta.get("classes", {}),
                "training_config": self._binary_meta.get("training_config", {}),
                "data": self._binary_meta.get("data", {}),
                "val_metrics": self._safe_val_metrics(self._binary_meta),
            },
            "multiclass": {
                "model_type": self._multiclass_meta.get("model_type"),
                "task": self._multiclass_meta.get("task"),
                "attack_classes": self._multiclass_meta.get("attack_classes", []),
                "num_classes": self._multiclass_meta.get("num_classes", 0),
                "training_config": self._multiclass_meta.get("training_config", {}),
                "data": self._multiclass_meta.get("data", {}),
                "val_metrics": self._safe_val_metrics(self._multiclass_meta),
            },
            "preprocessing": {
                "scaler_type": self._preprocessing.get("scaler", {}).get("type"),
                "fitted_on": self._preprocessing.get("scaler", {}).get("fitted_on"),
                "split": self._preprocessing.get("split", {}),
                "class_distribution": self._preprocessing.get("class_distribution", {}),
            },
        }

    def get_policy(self) -> dict:
        """Policy deny/quarantine lists and default action."""
        policy = self._policy.get("policy", {})
        return {
            "deny_classes": policy.get("deny_classes", []),
            "quarantine_classes": policy.get("quarantine_classes", []),
            "default_attack_action": policy.get("default_attack_action", "QUARANTINE"),
        }

    def get_eval(self) -> Optional[dict]:
        """Evaluation summary, or None if eval has not been run yet."""
        return self._eval_summary

    def get_config(self) -> dict:
        """Training and feature selection hyperparameters."""
        cfg = self._training_config or {}
        return {
            "feature_selection": cfg.get("feature_selection", {}),
            "binary_training": cfg.get("binary_training", {}),
            "multiclass_training": cfg.get("multiclass_training", {}),
            "evaluation": cfg.get("evaluation", {}),
        }

    # ----------------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> dict:
        """Load a JSON file or raise with a clear message."""
        if not path.exists():
            raise FileNotFoundError(f"MetaService: required file not found: {path}")
        with open(path, "r") as fh:
            return json.load(fh)

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """Load a YAML file or raise with a clear message."""
        if not path.exists():
            raise FileNotFoundError(f"MetaService: required file not found: {path}")
        with open(path, "r") as fh:
            return yaml.safe_load(fh) or {}

    @staticmethod
    def _load_json_optional(path: Path) -> Optional[dict]:
        """Load a JSON file if it exists, otherwise return None."""
        if not path.exists():
            logger.warning("MetaService: optional file not found (skipped): %s", path)
            return None
        with open(path, "r") as fh:
            return json.load(fh)

    @staticmethod
    def _safe_val_metrics(meta: dict) -> dict:
        """Extract val metrics, stripping the large confusion_matrix + classification_report."""
        vm = meta.get("val_metrics", {})
        return {
            "split": vm.get("split"),
            "accuracy": vm.get("accuracy"),
            "f1_weighted": vm.get("f1_weighted"),
            "f1_macro": vm.get("f1_macro"),
            "precision_weighted": vm.get("precision_weighted"),
            "recall_weighted": vm.get("recall_weighted"),
            "roc_auc": vm.get("roc_auc"),
        }
