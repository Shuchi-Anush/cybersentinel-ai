"""
CyberSentinel AI — Dashboard: Evaluation Page
Author: CyberSentinel ML-LAB

Binary and multiclass model evaluation metrics.
Data sources: GET /meta/models, GET /meta/eval
"""

import streamlit as st
import pandas as pd
from src.dashboard.api_client import get_api

st.header("📈 Evaluation")

api = get_api()

if not api.is_reachable():
    st.error("⚠️ API not reachable. Run API server first.")
    st.stop()

with st.spinner("📊 Extracting Performance Metrics..."):
    models = api.get_models()

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def fmt(val):
    """Safely format numeric values to 4 decimal places."""
    return f"{val:.4f}" if isinstance(val, (int, float)) else "—"


def build_metrics_df(metric_dict: dict, keys_map: dict) -> pd.DataFrame:
    """Build a DataFrame suitable for st.bar_chart from a metric dictionary."""
    return pd.DataFrame(
        [
            {"Metric": label, "Score": metric_dict.get(key)}
            for key, label in keys_map.items()
        ]
    )


# ------------------------------------------------------------------
# Tabs: Binary | Multi-class
# ------------------------------------------------------------------

tab_bin, tab_mc = st.tabs(["🎯 Binary Classifier", "🔍 Multi-class Classifier"])

# ==================================================================
# BINARY
# ==================================================================

with tab_bin:
    binary = models.get("binary", {})
    vm = binary.get("val_metrics", {})

    st.subheader("Validation Metrics")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Accuracy", fmt(vm.get("accuracy")))
    with c2:
        st.metric("F1 (weighted)", fmt(vm.get("f1_weighted")))
    with c3:
        st.metric("F1 (macro)", fmt(vm.get("f1_macro")))
    with c4:
        st.metric("Precision", fmt(vm.get("precision_weighted")))
    with c5:
        st.metric("ROC-AUC", fmt(vm.get("roc_auc")))

    # Binary Metrics Chart
    st.markdown("#### Performance Chart")
    bin_map = {
        "accuracy": "Accuracy",
        "f1_weighted": "F1 (weighted)",
        "f1_macro": "F1 (macro)",
        "precision_weighted": "Precision",
        "roc_auc": "ROC-AUC",
    }
    st.bar_chart(
        build_metrics_df(vm, bin_map).set_index("Metric"), width="stretch"
    )
    st.caption("Higher is better (0–1 scale)")

    st.divider()

    st.subheader("Per-Class Report")
    st.caption(
        "Detailed per-class report (precision/recall per class) is omitted from summary endpoints."
    )

    st.divider()

    # Model Info
    st.subheader("Model Info")
    data = binary.get("data", {})
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.markdown(f"**Model type:** `{binary.get('model_type', '—')}`")
        st.markdown(f"**Train rows:** {data.get('train_rows', '—'):,}")
        st.markdown(f"**Val rows:** {data.get('val_rows', '—'):,}")
        st.markdown(f"**Feature count:** {data.get('feature_count', '—')}")
    with info_col2:
        cfg = binary.get("training_config", {})
        st.markdown("**Training config:**")
        st.json(cfg, expanded=False)

# ==================================================================
# MULTI-CLASS
# ==================================================================

with tab_mc:
    multi = models.get("multiclass", {})
    mc_vm = multi.get("val_metrics", {})

    st.subheader("Validation Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Accuracy", fmt(mc_vm.get("accuracy")))
    with c2:
        st.metric("F1 (weighted)", fmt(mc_vm.get("f1_weighted")))
    with c3:
        st.metric("F1 (macro)", fmt(mc_vm.get("f1_macro")))
    with c4:
        st.metric("# Classes", multi.get("num_classes", 0))

    # Multiclass Metrics Chart
    st.markdown("#### Performance Chart")
    mc_map = {
        "accuracy": "Accuracy",
        "f1_weighted": "F1 (weighted)",
        "f1_macro": "F1 (macro)",
    }
    st.bar_chart(
        build_metrics_df(mc_vm, mc_map).set_index("Metric"), width="stretch"
    )
    st.caption("Higher is better (0–1 scale)")

    st.divider()

    st.subheader("Per-Class Report")
    st.caption(
        "Full per-class F1 metric charts are available in offline HTML files (`models/eval/`)."
    )

    # Attack class list
    st.subheader("Attack Classes")
    attack_classes = multi.get("attack_classes", [])
    if attack_classes:
        # Display as a 3-column grid of badges
        cols_per_row = 3
        for i in range(0, len(attack_classes), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(attack_classes):
                    col.markdown(f"- `{attack_classes[idx]}`")

    st.divider()

    st.subheader("Model Info")
    mc_data = multi.get("data", {})
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.markdown(f"**Model type:** `{multi.get('model_type', '—')}`")
        st.markdown(
            f"**Train rows (attack only):** {mc_data.get('train_attack_rows', '—'):,}"
        )
        st.markdown(
            f"**Val rows (attack only):** {mc_data.get('val_attack_rows', '—'):,}"
        )
        st.markdown(f"**Feature count:** {mc_data.get('feature_count', '—')}")
        st.caption(mc_data.get("note", ""))
    with info_col2:
        mc_cfg = multi.get("training_config", {})
        st.markdown("**Training config:**")
        st.json(mc_cfg, expanded=False)

# ------------------------------------------------------------------
# Eval report status
# ------------------------------------------------------------------

st.divider()
st.subheader("Holdout Data Evaluation")
eval_data = api.get_eval()

if not eval_data:
    st.warning(
        "⚠️ No held-out evaluation report found. "
        "Run the pipeline evaluation stage to generate full test-set metrics:\n\n"
        "```\nvenv\\Scripts\\python -m src.pipeline.pipeline_runner --eval-only\n```"
    )
else:
    st.success("✅ Held-out Evaluation Report Found")

    bin_eval = eval_data.get("binary", {})
    mc_eval = eval_data.get("multiclass", {})

    col_ebin, col_emc = st.columns(2)

    with col_ebin:
        st.markdown("#### Binary Model Test Metrics")
        m1, m2 = st.columns(2)
        m1.metric("Accuracy", fmt(bin_eval.get("accuracy")))
        m2.metric("ROC-AUC", fmt(bin_eval.get("roc_auc")))

    with col_emc:
        st.markdown("#### Multiclass Model Test Metrics")
        m1, m2 = st.columns(2)
        m1.metric("Accuracy", fmt(mc_eval.get("accuracy")))
        m2.metric("F1 (macro)", fmt(mc_eval.get("f1_macro")))

    # --------------------------------------------------------------
    # Per-Class Metrics
    # --------------------------------------------------------------
    roc_per_class = mc_eval.get("roc_auc_per_class", {})
    ap_per_class = mc_eval.get("average_precision_per_class", {})

    if roc_per_class and ap_per_class:
        st.subheader("📊 Per-Class Performance")

        # Merge lists into DataFrame
        classes = list(roc_per_class.keys())
        class_df = pd.DataFrame(
            {
                "Class": classes,
                "ROC-AUC": [roc_per_class.get(c, 0.0) for c in classes],
                "Average Precision": [ap_per_class.get(c, 0.0) for c in classes],
            }
        )

        # Sort by ROC-AUC before displaying table
        class_df = class_df.sort_values("ROC-AUC", ascending=False)

        # Display Table and Chart side-by-side
        pc1, pc2 = st.columns(2)
        with pc1:
            st.markdown("**Performance Table**")
            st.dataframe(class_df, width="stretch", hide_index=True)

        with pc2:
            st.markdown("**ROC-AUC Bar Chart**")
            st.bar_chart(
                class_df.set_index("Class")["ROC-AUC"], width="stretch"
            )

        # Highlight weakest classes
        weakest = class_df.sort_values(["Average Precision", "ROC-AUC"]).head(3)

        low_ap_classes = class_df[class_df["Average Precision"] < 0.9]

        weakest_labels = weakest["Class"].tolist()
        st.warning(
            f"⚠️ **Needs Attention!** The models showed the weakest performance against "
            f"the following 3 classes: `{', '.join(weakest_labels)}`."
        )

        if not low_ap_classes.empty:
            st.warning(
                f"⚠️ Classes with low Average Precision (<0.90): "
                f"{', '.join(low_ap_classes['Class'].tolist())}"
            )

        st.divider()
        st.subheader("🧠 Model Insight")

        mc_f1 = mc_eval.get("f1_macro", 0.0)
        mc_roc = mc_eval.get("roc_auc_macro", 0.0)
        mc_f1_w = mc_eval.get("f1_weighted", 0.0)

        # Separation Quality
        if mc_roc >= 0.95:
            st.success(
                f"🌟 **Strong Separation (ROC-AUC {mc_roc:.3f}):** The multiclass baseline effectively distinguishes most attack signatures with high confidence."
            )
        elif mc_roc >= 0.80:
            st.info(
                f"✅ **Adequate Separation (ROC-AUC {mc_roc:.3f}):** The model generally identifies attack boundaries, though overlapping signatures exist."
            )
        elif mc_roc > 0.0:
            st.warning(
                f"⚠️ **Weak Separation (ROC-AUC {mc_roc:.3f}):** The model struggles to separate classes robustly, leading to misclassifications."
            )

        # Imbalance penalty
        f1_gap = mc_f1_w - mc_f1
        if mc_f1 > 0 and f1_gap > 0.10:
            st.warning(
                f"⚖️ **Imbalance Penalty:** Macro F1 (`{mc_f1:.3f}`) is significantly lower than Weighted F1 (`{mc_f1_w:.3f}`). "
                "This performance gap indicates that severe class imbalance drags down accuracy on rare minority attacks."
            )
        elif mc_f1 > 0:
            st.success(
                f"⚖️ **Balanced Accuracy:** The narrow gap between Macro F1 (`{mc_f1:.3f}`) and Weighted F1 (`{mc_f1_w:.3f}`) "
                "indicates the model effectively counters major class imbalance artifacts."
            )

        # Precision-Recall context
        if not low_ap_classes.empty:
            weakest_str = ", ".join(low_ap_classes["Class"].head(3).tolist())
            st.error(
                f"🚨 **Precision vs Recall Gap:** Classes like `{weakest_str}` suffer from low Average Precision (<0.90). "
                "This indicates a severe precision-recall tradeoff—the model either misses these attacks (low recall) or guesses them too often (causing false positives)."
            )
        else:
            st.success(
                "🎯 **Robust Precision-Recall:** All classes maintain high Average Precision. The model effectively scales its decision boundaries without falling into false-positive volume traps."
            )

    # --------------------------------------------------------------
    # Confusion Matrix Visualization
    # --------------------------------------------------------------
    cm = mc_eval.get("confusion_matrix")
    cm_classes = mc_eval.get("attack_classes", [])

    if cm and cm_classes and len(cm) == len(cm_classes):
        st.divider()
        st.subheader("🧩 Confusion Matrix")
        st.caption("Rows: Actual Class | Columns: Predicted Class")

        cm_df = pd.DataFrame(cm, index=cm_classes, columns=cm_classes)

        normalize = st.checkbox("Normalize Confusion Matrix")
        if normalize:
            # GUARD: sum of row must be > 0 to avoid division by zero
            row_sums = cm_df.sum(axis=1)
            if (row_sums > 0).all():
                cm_df = cm_df.div(row_sums, axis=0)
                st.caption("Normalized per row (percentage of actual class)")
            else:
                st.warning("⚠️ Some classes have zero actual samples; skipping normalization.")

        # Apply a background gradient to mimic seaborn heatmap
        st.dataframe(cm_df.style.background_gradient(cmap="Blues"), width="stretch")
        st.caption(
            "Diagonal = correct predictions. Off-diagonal = misclassifications. "
            "Darker cells indicate higher frequency."
        )

    with st.expander("🔧 Debug: Full Evaluation JSON"):
        st.json(eval_data)

# ------------------------------------------------------------------
# Executive Summary
# ------------------------------------------------------------------
st.divider()
st.subheader("📌 Executive Summary")

# Data already loaded into mc_eval near Line 196
f1_macro = mc_eval.get("f1_macro", 0.0)

if f1_macro < 0.85:
    st.error(f"**Action Required:** Model struggles on minority attack classes (F1 Macro: {f1_macro:.4f})")
elif f1_macro < 0.90:
    st.warning(f"**Optimization Recommended:** Some attack classes need improvement (F1 Macro: {f1_macro:.4f})")
else:
    st.success(f"**Production Ready:** Model performs robustly across classes (F1 Macro: {f1_macro:.4f})")
