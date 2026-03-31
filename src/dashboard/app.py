"""
CyberSentinel AI — Dashboard
Author: CyberSentinel ML-LAB

Streamlit entry point.

    streamlit run src/dashboard/app.py

Multi-page layout: pages are auto-discovered from src/dashboard/pages/.
"""

import os
import sys
import time
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

    auto_refresh = st.checkbox("🔄 Auto Refresh (10s)", value=False, help="Automatically refresh the dashboard every 10 seconds.")
    if auto_refresh:
        time.sleep(10)
        st.rerun()

    st.divider()
    st.caption("© 2026 CyberSentinel ML-LAB")
    st.caption(f"**Target:** {api.base_url}")
    st.caption(f"**Env:** {os.environ.get('ENVIRONMENT', 'Production')}")

# ------------------------------------------------------------------
# Landing page (shown when no sub-page is selected)
# ------------------------------------------------------------------

st.title("🛡️ CyberSentinel AI Dashboard")
st.markdown("> **Real-time intrusion detection with policy-driven response**")

# Quick status metrics row (Requirement A)
api = get_api()
health = api.health()
models = api.get_models()

col1, col2, col3 = st.columns(3)
with col1:
    status = "🟢 Online" if "error" not in health and health.get("status") == "ok" else "🔴 Offline"
    st.metric("API Status", status)
with col2:
    pipeline = "🟢 Loaded" if health.get("pipeline_loaded") else "🔴 Missing"
    st.metric("Inference Pipeline", pipeline)
with col3:
    n_classes = models.get("multiclass", {}).get("num_classes", "0")
    st.metric("Attack Classes", n_classes)

st.divider()

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

# Cleaned up redundant status cards block
