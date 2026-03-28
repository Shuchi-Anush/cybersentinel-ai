"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Evaluator (Stage 5)
Author: CyberSentinel ML-LAB

Computes and saves comprehensive evaluation reports for both the binary
classifier and the multi-class attack-type classifier.

Outputs per model (saved to EVAL_DIR / "binary" and EVAL_DIR / "multiclass"):
    metrics.json          — all scalar metrics (accuracy, F1, ROC-AUC, etc.)
    classification_report.json
    confusion_matrix.png
    roc_curve.png         — binary only (one curve)
    pr_curve.png          — binary only
    roc_curves_ova.png    — multiclass  (one-vs-all ROC per class)
    pr_curves_ova.png     — multiclass  (one-vs-all PR per class)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive backend; safe in all environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import LabelBinarizer

from src.features.preprocessor import load_splits
from src.training.binary_trainer import load_binary_model
from src.training.multiclass_trainer import load_multiclass_model

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("evaluator")

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

from src.core.paths import EVAL_DIR

EVAL_ROOT = EVAL_DIR
BINARY_EVAL_DIR = EVAL_ROOT / "binary"
MULTICLASS_EVAL_DIR = EVAL_ROOT / "multiclass"

# ------------------------------------------------------------------
# Plot style
# ------------------------------------------------------------------

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
    }
)
CMAP = "Blues"


# ==================================================================
# Binary Evaluation
# ==================================================================


def _plot_confusion_matrix_binary(cm: np.ndarray, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, interpolation="nearest", cmap=CMAP)
    fig.colorbar(im, ax=ax)
    tick_marks = [0, 1]
    ax.set_xticks(tick_marks)
    ax.set_yticks(tick_marks)
    ax.set_xticklabels(["Benign (0)", "Attack (1)"])
    ax.set_yticklabels(["Benign (0)", "Attack (1)"])
    thresh = cm.max() / 2.0
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                f"{cm[i, j]:,}",
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=11,
            )
    ax.set_title("Binary Classifier — Confusion Matrix (Test Set)")
    ax.set_ylabel("Actual")
    ax.set_xlabel("Predicted")
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png")
    plt.close(fig)


def _plot_roc_binary(y_true: pd.Series, y_proba: np.ndarray, out_dir: Path) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    roc_auc = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#2563EB", lw=2, label=f"ROC (AUC = {roc_auc:.4f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.02])
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Binary Classifier — ROC Curve (Test Set)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_dir / "roc_curve.png")
    plt.close(fig)
    return roc_auc


def _plot_pr_binary(y_true: pd.Series, y_proba: np.ndarray, out_dir: Path) -> float:
    precision, recall, _ = precision_recall_curve(y_true, y_proba)
    avg_prec = average_precision_score(y_true, y_proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, color="#DC2626", lw=2, label=f"PR (AP = {avg_prec:.4f})")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Binary Classifier — Precision-Recall Curve (Test Set)")
    ax.legend(loc="upper right")
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    fig.tight_layout()
    fig.savefig(out_dir / "pr_curve.png")
    plt.close(fig)
    return avg_prec


def evaluate_binary(
    out_dir: Optional[Path] = None,
    split: str = "test",
) -> dict:
    """
    Evaluate the binary classifier on the specified split.

    Loads the saved model from MODELS_DIR / "binary" and the split from
    DATA_DIR / "processed".  Saves plots and metrics to EVAL_DIR / "binary".

    Parameters
    ----------
    out_dir : Path, optional
        Override default output directory.
    split : str
        Which parquet split to evaluate on ('test', 'val', or 'train').

    Returns
    -------
    dict
        All computed scalar metrics.
    """
    t0 = time.time()
    out_dir = out_dir or BINARY_EVAL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Evaluating binary classifier on '%s' split…", split)
    x, y_binary, _ = load_splits(split)
    model = load_binary_model()

    y_pred = model.predict(x)
    y_proba = model.predict_proba(x)[:, 1]

    # ---- scalar metrics ------------------------------------------------
    report_dict = classification_report(
        y_binary, y_pred, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y_binary, y_pred)

    roc_auc = _plot_roc_binary(y_binary, y_proba, out_dir)
    avg_prec = _plot_pr_binary(y_binary, y_proba, out_dir)
    _plot_confusion_matrix_binary(cm, out_dir)

    metrics = {
        "task": "binary_classification",
        "split": split,
        "accuracy": round(float(report_dict["accuracy"]), 6),
        "f1_weighted": round(
            float(f1_score(y_binary, y_pred, average="weighted", zero_division=0)), 6
        ),
        "f1_macro": round(
            float(f1_score(y_binary, y_pred, average="macro", zero_division=0)), 6
        ),
        "precision_weighted": round(
            float(
                precision_score(y_binary, y_pred, average="weighted", zero_division=0)
            ),
            6,
        ),
        "recall_weighted": round(
            float(recall_score(y_binary, y_pred, average="weighted", zero_division=0)),
            6,
        ),
        "roc_auc": round(roc_auc, 6),
        "average_precision": round(avg_prec, 6),
        "confusion_matrix": cm.tolist(),
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    # ---- save reports --------------------------------------------------
    with open(out_dir / "metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2)
    with open(out_dir / "classification_report.json", "w") as fh:
        json.dump(report_dict, fh, indent=2)

    logger.info(
        "[BINARY %s] Accuracy=%.4f  F1(w)=%.4f  ROC-AUC=%.4f  AP=%.4f",
        split.upper(),
        metrics["accuracy"],
        metrics["f1_weighted"],
        metrics["roc_auc"],
        metrics["average_precision"],
    )
    return metrics


# ==================================================================
# Multi-class Evaluation
# ==================================================================


def _plot_confusion_matrix_multiclass(
    cm: np.ndarray, class_names: list[str], out_dir: Path
) -> None:
    n = len(class_names)
    fig_size = max(8, n)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size - 1))
    im = ax.imshow(cm, interpolation="nearest", cmap=CMAP)
    fig.colorbar(im, ax=ax, fraction=0.03)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(class_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(class_names, fontsize=8)
    thresh = cm.max() / 2.0
    for i in range(n):
        for j in range(n):
            ax.text(
                j,
                i,
                str(cm[i, j]),
                ha="center",
                va="center",
                fontsize=7,
                color="white" if cm[i, j] > thresh else "black",
            )
    ax.set_title("Multi-class Classifier — Confusion Matrix (Test Set)")
    ax.set_ylabel("Actual")
    ax.set_xlabel("Predicted")
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrix.png")
    plt.close(fig)


def _plot_roc_ova(
    y_bin: np.ndarray,
    y_proba: np.ndarray,
    class_names: list[str],
    out_dir: Path,
) -> dict[str, float]:
    """One-vs-All ROC curves, one per attack class."""
    n_classes = len(class_names)
    aucs: dict[str, float] = {}
    fig, ax = plt.subplots(figsize=(9, 7))
    colours = plt.cm.tab10(np.linspace(0, 1, n_classes))  # type: ignore[attr-defined]

    for i, (cls_name, colour) in enumerate(zip(class_names, colours)):
        if y_bin[:, i].sum() == 0:
            continue  # class absent in this split — skip
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
        roc_auc = auc(fpr, tpr)
        aucs[cls_name] = round(roc_auc, 6)
        ax.plot(
            fpr, tpr, color=colour, lw=1.5, label=f"{cls_name[:20]} ({roc_auc:.3f})"
        )

    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.02])
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Multi-class Classifier — OVA ROC Curves (Test Set)")
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "roc_curves_ova.png")
    plt.close(fig)
    return aucs


def _plot_pr_ova(
    y_bin: np.ndarray,
    y_proba: np.ndarray,
    class_names: list[str],
    out_dir: Path,
) -> dict[str, float]:
    """One-vs-All PR curves, one per attack class."""
    n_classes = len(class_names)
    avg_precs: dict[str, float] = {}
    fig, ax = plt.subplots(figsize=(9, 7))
    colours = plt.cm.tab10(np.linspace(0, 1, n_classes))  # type: ignore[attr-defined]

    for i, (cls_name, colour) in enumerate(zip(class_names, colours)):
        if y_bin[:, i].sum() == 0:
            continue
        prec, rec, _ = precision_recall_curve(y_bin[:, i], y_proba[:, i])
        ap = average_precision_score(y_bin[:, i], y_proba[:, i])
        avg_precs[cls_name] = round(ap, 6)
        ax.plot(rec, prec, color=colour, lw=1.5, label=f"{cls_name[:20]} (AP={ap:.3f})")

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Multi-class Classifier — OVA PR Curves (Test Set)")
    ax.legend(loc="upper right", fontsize=7)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    fig.tight_layout()
    fig.savefig(out_dir / "pr_curves_ova.png")
    plt.close(fig)
    return avg_precs


def evaluate_multiclass(
    out_dir: Optional[Path] = None,
    split: str = "test",
) -> dict:
    """
    Evaluate the multi-class attack classifier on the specified split.

    Only attack rows (binary == 1) are evaluated — matching how the model
    was trained.  Saves plots and metrics to EVAL_DIR / "multiclass".

    Parameters
    ----------
    out_dir : Path, optional
        Override default output directory.
    split : str
        Which parquet split to evaluate ('test', 'val', or 'train').

    Returns
    -------
    dict
        All computed scalar metrics.
    """
    t0 = time.time()
    out_dir = out_dir or MULTICLASS_EVAL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Evaluating multi-class classifier on '%s' split (attack rows only)…", split
    )

    x_full, y_binary, y_label = load_splits(split)
    model, encoder = load_multiclass_model()

    # Filter to attack rows only
    attack_mask = y_binary == 1
    x_attacks = x_full[attack_mask].reset_index(drop=True)
    y_label_attacks = y_label[attack_mask].reset_index(drop=True)

    # Filter to classes the encoder knows
    known_classes = set(encoder.classes_)
    known_mask = y_label_attacks.isin(known_classes)
    unseen = (~known_mask).sum()
    if unseen > 0:
        logger.warning("%d rows with unseen attack classes excluded from eval.", unseen)
    x_attacks = x_attacks[known_mask].reset_index(drop=True)
    y_label_attacks = y_label_attacks[known_mask].reset_index(drop=True)

    y_encoded = encoder.transform(y_label_attacks)
    y_pred = model.predict(x_attacks)
    y_proba = model.predict_proba(x_attacks)

    class_names: list[str] = encoder.classes_.tolist()

    # ---- per-class report --------------------------------------------
    report_dict = classification_report(
        y_encoded,
        y_pred,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    # ---- confusion matrix -------------------------------------------
    cm = confusion_matrix(y_encoded, y_pred)
    _plot_confusion_matrix_multiclass(cm, class_names, out_dir)

    # ---- OVA ROC / PR -----------------------------------------------
    lb = LabelBinarizer()
    y_bin = lb.fit_transform(y_encoded)
    # LabelBinarizer returns (n, 1) for binary; guard against it
    if y_bin.shape[1] == 1:
        y_bin = np.hstack([1 - y_bin, y_bin])

    roc_aucs_per_class = _plot_roc_ova(y_bin, y_proba, class_names, out_dir)
    pr_aps_per_class = _plot_pr_ova(y_bin, y_proba, class_names, out_dir)

    # ---- macro/weighted ROC-AUC -------------------------------------
    try:
        roc_auc_macro = round(
            float(
                roc_auc_score(y_encoded, y_proba, multi_class="ovr", average="macro")
            ),
            6,
        )
        roc_auc_weighted = round(
            float(
                roc_auc_score(y_encoded, y_proba, multi_class="ovr", average="weighted")
            ),
            6,
        )
    except ValueError:
        roc_auc_macro = roc_auc_weighted = None

    metrics = {
        "task": "multiclass_attack_classification",
        "split": split,
        "num_classes": int(len(class_names)),
        "attack_classes": class_names,
        "eval_rows": int(len(x_attacks)),
        "unseen_rows_excluded": int(unseen),
        "accuracy": round(float(report_dict["accuracy"]), 6),
        "f1_weighted": round(
            float(f1_score(y_encoded, y_pred, average="weighted", zero_division=0)), 6
        ),
        "f1_macro": round(
            float(f1_score(y_encoded, y_pred, average="macro", zero_division=0)), 6
        ),
        "precision_weighted": round(
            float(
                precision_score(y_encoded, y_pred, average="weighted", zero_division=0)
            ),
            6,
        ),
        "recall_weighted": round(
            float(recall_score(y_encoded, y_pred, average="weighted", zero_division=0)),
            6,
        ),
        "roc_auc_macro": roc_auc_macro,
        "roc_auc_weighted": roc_auc_weighted,
        "roc_auc_per_class": roc_aucs_per_class,
        "average_precision_per_class": pr_aps_per_class,
        "confusion_matrix": cm.tolist(),
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    with open(out_dir / "metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2)
    with open(out_dir / "classification_report.json", "w") as fh:
        json.dump(report_dict, fh, indent=2)

    logger.info(
        "[MULTICLASS %s] Accuracy=%.4f  F1(w)=%.4f  F1(macro)=%.4f  ROC-AUC(macro)=%s",
        split.upper(),
        metrics["accuracy"],
        metrics["f1_weighted"],
        metrics["f1_macro"],
        metrics["roc_auc_macro"],
    )
    return metrics


# ==================================================================
# Orchestrator — evaluate both models
# ==================================================================


def run_evaluation(
    split: str = "test",
    binary_out_dir: Optional[Path] = None,
    multiclass_out_dir: Optional[Path] = None,
) -> dict:
    """
    Evaluate both the binary and multi-class classifiers.

    Parameters
    ----------
    split : str
        Parquet split to evaluate on ('test', 'val', or 'train').
    binary_out_dir : Path, optional
        Override binary eval output directory.
    multiclass_out_dir : Path, optional
        Override multiclass eval output directory.

    Returns
    -------
    dict
        Keys: 'binary' → binary metrics dict,
              'multiclass' → multiclass metrics dict.
    """
    t0 = time.time()
    logger.info("=" * 55)
    logger.info("Starting evaluation pipeline (split='%s')…", split)
    logger.info("=" * 55)

    binary_metrics = evaluate_binary(out_dir=binary_out_dir, split=split)
    multiclass_metrics = evaluate_multiclass(out_dir=multiclass_out_dir, split=split)

    elapsed = round(time.time() - t0, 2)

    # ---- combined summary report ------------------------------------
    combined = {
        "split": split,
        "binary": binary_metrics,
        "multiclass": multiclass_metrics,
        "total_elapsed_seconds": elapsed,
    }
    eval_root = (binary_out_dir or BINARY_EVAL_DIR).parent
    with open(eval_root / "summary.json", "w") as fh:
        json.dump(combined, fh, indent=2)

    # ---- artifacts/metrics.json (consistent production persistence) ----
    from src.core.paths import ARTIFACTS_DIR
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    production_metrics = {
        "binary": {
            "accuracy": binary_metrics["accuracy"],
            "f1": binary_metrics["f1_weighted"],
        },
        "multiclass": {
            "accuracy": multiclass_metrics["accuracy"],
            "f1_macro": multiclass_metrics["f1_macro"],
        },
    }
    with open(ARTIFACTS_DIR / "metrics.json", "w") as fh:
        json.dump(production_metrics, fh, indent=2)

    _print_summary(binary_metrics, multiclass_metrics, elapsed)
    return combined


def _print_summary(binary: dict, multiclass: dict, elapsed: float) -> None:
    print("\n" + "=" * 60)
    print("  Evaluation Summary")
    print("=" * 60)
    print(f"\n  Binary Classifier ({binary['split']} set):")
    print(f"    Accuracy       : {binary['accuracy']:.4f}")
    print(f"    F1 (weighted)  : {binary['f1_weighted']:.4f}")
    print(f"    F1 (macro)     : {binary['f1_macro']:.4f}")
    print(f"    ROC-AUC        : {binary['roc_auc']:.4f}")
    print(f"    Avg Precision  : {binary['average_precision']:.4f}")
    print(f"\n  Multi-class Classifier ({multiclass['split']} set — attack rows only):")
    print(f"    Classes        : {multiclass['num_classes']}")
    print(f"    Accuracy       : {multiclass['accuracy']:.4f}")
    print(f"    F1 (weighted)  : {multiclass['f1_weighted']:.4f}")
    print(f"    F1 (macro)     : {multiclass['f1_macro']:.4f}")
    roc = multiclass["roc_auc_macro"]
    print(f"    ROC-AUC (macro): {roc:.4f}" if roc else "    ROC-AUC (macro): N/A")
    print(f"\n  Reports saved to : {EVAL_DIR}")
    print(f"  Total elapsed    : {elapsed:.1f}s")
    print("=" * 60)


# ==================================================================
# CLI
# ==================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Evaluation (Stage 5)"
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        choices=["train", "val", "test"],
        help="Which data split to evaluate on (default: test)",
    )
    parser.add_argument(
        "--binary-only", action="store_true", help="Only evaluate the binary classifier"
    )
    parser.add_argument(
        "--multiclass-only",
        action="store_true",
        help="Only evaluate the multi-class classifier",
    )
    args = parser.parse_args()

    if args.binary_only:
        evaluate_binary(split=args.split)
    elif args.multiclass_only:
        evaluate_multiclass(split=args.split)
    else:
        run_evaluation(split=args.split)
