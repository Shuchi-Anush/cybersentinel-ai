"""
CyberSentinel AI — models package

Public API
----------
    from src.models import run_evaluation, evaluate_binary, evaluate_multiclass
"""
from src.models.evaluator import (
    run_evaluation,
    evaluate_binary,
    evaluate_multiclass,
)

__all__ = [
    "run_evaluation",
    "evaluate_binary",
    "evaluate_multiclass",
]
