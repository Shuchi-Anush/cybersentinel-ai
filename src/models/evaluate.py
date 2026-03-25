"""
CyberSentinel AI — src/models/evaluate.py

Legacy compatibility shim.
New code should use:  from src.models.evaluator import run_evaluation
"""
from src.models.evaluator import run_evaluation, evaluate_binary, evaluate_multiclass


def evaluate_model(model, x_test, y_test):
    """
    Legacy shim kept for backward compatibility with stage_05_evaluation.py stub.
    Delegates to the new run_evaluation() — model/x_test/y_test args are ignored
    since the new evaluator loads from disk directly.
    """
    return run_evaluation(split="test")
