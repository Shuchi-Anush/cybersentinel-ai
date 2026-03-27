"""
CyberSentinel AI — Dashboard
Author: CyberSentinel ML-LAB

Streamlit entry point.

    streamlit run src/dashboard/app.py

Multi-page layout: pages are auto-discovered from src/dashboard/pages/.
"""

import sys
from pathlib import Path

# ✅ MUST come before any src imports
sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st
from src.dashboard.api_client import get_api
# ------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ------------------------------------------------------------------

st.set_page_config(
    page_title="CyberSentinel AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Sidebar branding
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("# 🛡️ CyberSentinel AI")
    st.caption("Intrusion Detection System")
    st.divider()

    # API connection status
    api = get_api()
    if api.is_reachable():
        st.success("API Connected", icon="✅")
    else:
        st.error("API Unreachable", icon="🔴")
        st.info(
            f"Start the API server first:\n\n"
            f"```\nuvicorn src.api.main:app --reload\n```\n\n"
            f"**Target:** `{api.base_url}`"
        )

    st.divider()
    st.caption("© 2026 CyberSentinel ML-LAB")

# ------------------------------------------------------------------
# Landing page (shown when no sub-page is selected)
# ------------------------------------------------------------------

st.title("🛡️ CyberSentinel AI Dashboard")
st.markdown(
    """
    Welcome to the CyberSentinel Intrusion Detection System dashboard.

    Use the **sidebar** to navigate between pages:

    | Page | Purpose |
    |---|---|
    | **Overview** | Pipeline health, model metadata, feature importances |
    | **Predict** | Single-flow and batch prediction |
    | **Evaluation** | Model performance metrics |
    | **Policy** | Active firewall policy rules |
    """
)

# Quick status cards
api = get_api()
if api.is_reachable():
    try:
        health = api.health()
        col1, col2, col3 = st.columns(3)
        with col1:
            status = "🟢 Online" if health.get("pipeline_loaded") else "🔴 Offline"
            st.metric("Pipeline", status)
        with col2:
            meta = "🟢 Loaded" if health.get("meta_loaded") else "🔴 Missing"
            st.metric("Metadata", meta)
        with col3:
            models = api.get_models()
            n_classes = models.get("multiclass", {}).get("num_classes", "?")
            st.metric("Attack Classes", n_classes)
    except Exception as e:
        st.warning(f"Could not load status: {e}")
