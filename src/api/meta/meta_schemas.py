"""
CyberSentinel AI — Meta Endpoint Schemas
Author: CyberSentinel ML-LAB

Pydantic response models for the /meta/* GET endpoints.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# /meta/features
# ------------------------------------------------------------------


class FeaturesResponse(BaseModel):
    """Selected features and their importances."""

    feature_count: int
    features: List[str]
    binary_importances: Dict[str, float] = Field(
        default_factory=dict,
        description="Top-20 feature importances from the binary model",
    )
    multiclass_importances: Dict[str, float] = Field(
        default_factory=dict,
        description="Top-20 feature importances from the multiclass model",
    )


# ------------------------------------------------------------------
# /meta/models
# ------------------------------------------------------------------


class ValMetrics(BaseModel):
    """Compact validation metrics (large CM / report excluded)."""

    split: Optional[str] = None
    accuracy: Optional[float] = None
    f1_weighted: Optional[float] = None
    f1_macro: Optional[float] = None
    precision_weighted: Optional[float] = None
    recall_weighted: Optional[float] = None
    roc_auc: Optional[float] = None


class BinaryModelInfo(BaseModel):
    model_type: Optional[str] = None
    task: Optional[str] = None
    classes: Dict[str, str] = Field(default_factory=dict)
    training_config: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)
    val_metrics: ValMetrics = Field(default_factory=ValMetrics)


class MulticlassModelInfo(BaseModel):
    model_type: Optional[str] = None
    task: Optional[str] = None
    attack_classes: List[str] = Field(default_factory=list)
    num_classes: int = 0
    training_config: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)
    val_metrics: ValMetrics = Field(default_factory=ValMetrics)


class PreprocessingInfo(BaseModel):
    scaler_type: Optional[str] = None
    fitted_on: Optional[str] = None
    split: dict = Field(default_factory=dict)
    class_distribution: dict = Field(default_factory=dict)


class ModelsResponse(BaseModel):
    """Combined model metadata."""

    binary: BinaryModelInfo
    multiclass: MulticlassModelInfo
    preprocessing: PreprocessingInfo


# ------------------------------------------------------------------
# /meta/policy
# ------------------------------------------------------------------


class PolicyResponse(BaseModel):
    """Active policy configuration."""

    deny_classes: List[str] = Field(default_factory=list)
    quarantine_classes: List[str] = Field(default_factory=list)
    default_attack_action: str = "QUARANTINE"


# ------------------------------------------------------------------
# /meta/eval
# ------------------------------------------------------------------


class EvalResponse(BaseModel):
    """Strict evaluation summary response (Contract enforced)."""

    f1_macro: float = Field(0.0, description="Macro-averaged F1 score on the test set")
    status: str = Field("missing", description="Status of the evaluation data (ok/missing)")


# ------------------------------------------------------------------
# /meta/config
# ------------------------------------------------------------------


class ConfigResponse(BaseModel):
    """Training and feature selection hyperparameters."""

    feature_selection: dict = Field(default_factory=dict)
    binary_training: dict = Field(default_factory=dict)
    multiclass_training: dict = Field(default_factory=dict)
    evaluation: dict = Field(default_factory=dict)
