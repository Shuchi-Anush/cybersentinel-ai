"""
CyberSentinel AI — Pipeline Stage 05: Evaluation
Delegates to src.models.evaluator (Stage 5 implementation).
"""

from src.models.evaluator import run_evaluation


def run_stage_05_evaluation(split: str = "test") -> dict:
    """
    Execute Stage 5 evaluation on both binary and multi-class models.

    Loads test split from DATA_DIR / "processed", runs both models, computes
    all metrics, saves JSON reports and PNG plots to EVAL_DIR.

    Parameters
    ----------
    split : str
        Data split to evaluate on ('test', 'val', or 'train').

    Returns
    -------
    dict
        Keys 'binary' and 'multiclass', each containing a metrics dict.
    """
    print(f"\n--- Stage 5: Evaluation (split='{split}') ---")
    results = run_evaluation(split=split)
    return results
