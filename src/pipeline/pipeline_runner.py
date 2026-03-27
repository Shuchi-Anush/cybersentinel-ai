"""
CyberSentinel AI — Pipeline Runner
Orchestrates all stages in sequence using the new modular API.

Usage:
    python -m src.pipeline.pipeline_runner
    python -m src.pipeline.pipeline_runner --skip-training
    python -m src.pipeline.pipeline_runner --eval-only
"""

from src.features.selector import run_feature_selection
from src.features.preprocessor import run_preprocessing
from src.training.binary_trainer import train_binary_classifier
from src.training.multiclass_trainer import train_multiclass_classifier
from src.models.evaluator import run_evaluation


def run_pipeline(skip_training: bool = False, eval_only: bool = False) -> dict:
    """
    Execute the full CyberSentinel-AI training pipeline.

    Parameters
    ----------
    skip_training : bool
        If True, skip Stages 1-4 and only run evaluation.
    eval_only : bool
        Alias for skip_training.

    Returns
    -------
    dict
        Combined results from all executed stages.
    """
    results = {}

    if not (skip_training or eval_only):
        # Stage 1 — Feature Selection
        print("\n--- Stage 1: Feature Selection ---")
        features = run_feature_selection()
        results["selected_features"] = features

        # Stage 2 — Preprocessing
        print("\n--- Stage 2: Preprocessing ---")
        splits = run_preprocessing()
        results["splits"] = {k: v.shape for k, v in splits.items()}

        # Stage 3 — Binary Classifier Training
        print("\n--- Stage 3: Binary Classifier Training ---")
        binary_model = train_binary_classifier()
        results["binary_model"] = type(binary_model).__name__

        # Stage 4 — Multi-class Classifier Training
        print("\n--- Stage 4: Multi-class Classifier Training ---")
        mc_model, encoder = train_multiclass_classifier()
        results["multiclass_model"] = type(mc_model).__name__
        results["attack_classes"] = encoder.classes_.tolist()

    # Stage 5 — Evaluation
    print("\n--- Stage 5: Evaluation ---")
    eval_results = run_evaluation(split="test")
    results["evaluation"] = {
        "binary_accuracy": eval_results["binary"]["accuracy"],
        "multiclass_accuracy": eval_results["multiclass"]["accuracy"],
    }

    print("\n Pipeline completed successfully.")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Full Pipeline Runner"
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip Stages 1-4, only run evaluation",
    )
    parser.add_argument(
        "--eval-only", action="store_true", help="Alias for --skip-training"
    )
    args = parser.parse_args()

    run_pipeline(skip_training=args.skip_training, eval_only=args.eval_only)
