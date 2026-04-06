"""
CyberSentinel AI — Dashboard: Overview Page
Author: CyberSentinel ML-LAB

Shows pipeline health, model metadata, feature importances, and training config.
Data sources: GET /health, /meta/models, /meta/features, /meta/config
"""

import streamlit as st
import pandas as pd
from src.dashboard.api_client import get_api

st.header("📊 Overview")

api = get_api()

# ------------------------------------------------------------------
# Connection guard
# ------------------------------------------------------------------

try:
    health = api.health()
    api_online = True
except Exception:
    api_online = False

if not api_online:
    st.error("⚠️ API not reachable. Run API server first.")
    st.stop()

# ------------------------------------------------------------------
# 1. Pipeline Health
# ------------------------------------------------------------------

st.subheader("Pipeline Status")

with st.spinner("Loading System Overview..."):
    health = api.health()
    models = api.get_models()
    features = api.get_features()
    config = api.get_config()

# ------------------------------------------------------------------
# 1. Pipeline Health
# ------------------------------------------------------------------
# Pipeline Status Calculation (Hierarchical)
if not api_online:
    pipeline_status = "🔴 Offline"
elif health.get("pipeline_error") is not None:
    pipeline_status = "🔴 Error"
elif health.get("pipeline_ready"):
    pipeline_status = "🟢 Online"
else:
    pipeline_status = "🟡 Loading"

# Metadata Status Calculation
metadata_status = (
    "🔴 Offline" if not api_online else 
    "🟢 Available" if health.get("meta_ready") else 
    "🔴 Missing"
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Inference Pipeline", pipeline_status)
with col2:
    st.metric("Metadata Service", metadata_status)
with col3:
    st.metric("API Status", health.get("status", "unknown").upper())

# ------------------------------------------------------------------
# 1.5 System Health Score
# ------------------------------------------------------------------
st.subheader("🧠 System Health Score")

binary_acc = models.get("binary", {}).get("val_metrics", {}).get("accuracy", 0.0)
multi_acc = models.get("multiclass", {}).get("val_metrics", {}).get("accuracy", 0.0)

# Weighted score: 40% Binary accuracy, 60% Multiclass accuracy
health_score = (0.4 * binary_acc) + (0.6 * multi_acc)

st.metric(
    label="Overall Health",
    value=f"{health_score * 100:.2f}%",
    delta=f"{health_score:.4f}",
    help="Weighted aggregate of binary (40%) and multiclass (60%) validation accuracies."
)

st.divider()

# ------------------------------------------------------------------
# 2. Model Summary Cards
# ------------------------------------------------------------------
st.subheader("Model Summary")

binary = models.get("binary", {})
multi = models.get("multiclass", {})
preproc = models.get("preprocessing", {})

col_b, col_m = st.columns(2)

with col_b:
    st.markdown("#### 🎯 Binary Classifier")
    b_vm = binary.get("val_metrics", {})
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Accuracy", f"{b_vm.get('accuracy', 0.0):.4f}")
    with m2:
        st.metric("F1 (weighted)", f"{b_vm.get('f1_weighted', 0.0):.4f}")
    with m3:
        st.metric("ROC-AUC", f"{b_vm.get('roc_auc', 0.0):.4f}")
    st.caption(
        f"Model: {binary.get('model_type', '—')} · Classes: {binary.get('classes', {})}"
    )

with col_m:
    st.markdown("#### 🔍 Multi-class Classifier")
    mc_vm = multi.get("val_metrics", {})
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Accuracy", f"{mc_vm.get('accuracy', 0.0):.4f}")
    with m2:
        st.metric("F1 (macro)", f"{mc_vm.get('f1_macro', 0.0):.4f}")
    with m3:
        st.metric("Attack Classes", multi.get("num_classes", 0))
    classes_str = ", ".join(multi.get("attack_classes", [])[:5])
    st.caption(f"Model: {multi.get('model_type', '—')} · Classes: {classes_str}…")

st.divider()

# ------------------------------------------------------------------
# 3. Data Statistics
# ------------------------------------------------------------------

st.subheader("Data Statistics")

split = preproc.get("split", {})
dist = preproc.get("class_distribution", {})

col_s, col_d = st.columns(2)

with col_s:
    st.markdown("**Split Sizes**")
    split_df = pd.DataFrame(
        [
            {"Split": "Train", "Rows": split.get("train_rows", 0)},
            {"Split": "Validation", "Rows": split.get("val_rows", 0)},
            {"Split": "Test", "Rows": split.get("test_rows", 0)},
        ]
    )
    st.dataframe(split_df, hide_index=True, width="stretch")

with col_d:
    st.markdown("**Class Distribution (Train)**")
    train_dist = dist.get("train", {})
    if train_dist:
        dist_df = pd.DataFrame(
            [
                {"Class": "Benign (0)", "Count": train_dist.get("0", 0)},
                {"Class": "Attack (1)", "Count": train_dist.get("1", 0)},
            ]
        )
        st.bar_chart(dist_df.set_index("Class"), width="stretch")

st.divider()

# ------------------------------------------------------------------
# 4. Feature Importances
# ------------------------------------------------------------------

st.subheader("Feature Importances (Top 20)")

view = st.radio(
    "Model",
    ["Binary Classifier", "Multi-class Classifier"],
    horizontal=True,
    label_visibility="collapsed",
)

if view == "Binary Classifier":
    importances = features.get("binary_importances", {})
else:
    importances = features.get("multiclass_importances", {})

if importances:
    imp_df = pd.DataFrame(
        {"Feature": list(importances.keys()), "Importance": list(importances.values())}
    ).sort_values("Importance", ascending=True)
    st.bar_chart(imp_df.set_index("Feature"), horizontal=True, width="stretch")
    st.caption(f"Total selected features: {features.get('feature_count', '?')}")
else:
    st.info("No feature importances available.")

st.divider()

# ------------------------------------------------------------------
# 5. Training Configuration
# ------------------------------------------------------------------

st.subheader("Training Configuration")

tab_fs, tab_bt, tab_mt = st.tabs(
    ["Feature Selection", "Binary Training", "Multi-class Training"]
)

with tab_fs:
    fs = config.get("feature_selection", {})
    if fs:
        for k, v in fs.items():
            st.text(f"{k}: {v}")
    else:
        st.info("No feature selection config.")

with tab_bt:
    bt = config.get("binary_training", {})
    if bt:
        for k, v in bt.items():
            st.text(f"{k}: {v}")
    else:
        st.info("No binary training config.")

with tab_mt:
    mt = config.get("multiclass_training", {})
    if mt:
        for k, v in mt.items():
            st.text(f"{k}: {v}")
    else:
        st.info("No multiclass training config.")
