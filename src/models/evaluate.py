"""
CyberSentinel AI — src/models/evaluate.py

Legacy compatibility shim.
New code should use:  from src.models.evaluator import run_evaluation
"""

from src.models.evaluator import run_evaluation


def evaluate_model(*args, **kwargs):
    """
    Legacy shim: arguments model, x_test, y_test are ignored as the 
    standardized evaluation flow now handles its own data/model loading.
    """
    # legacy shim — arguments ignored
    return run_evaluation(split="test")
