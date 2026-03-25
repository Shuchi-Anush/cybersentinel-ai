"""
CyberSentinel AI — training package

Public API
----------
    from src.training import train_binary_classifier, load_binary_model
    from src.training import train_multiclass_classifier, load_multiclass_model
"""

from src.training.binary_trainer import (
    train_binary_classifier,
    load_binary_model,
)
from src.training.multiclass_trainer import (
    train_multiclass_classifier,
    load_multiclass_model,
)

__all__ = [
    # Stage 3 — Binary
    "train_binary_classifier",
    "load_binary_model",
    # Stage 4 — Multi-class
    "train_multiclass_classifier",
    "load_multiclass_model",
]
