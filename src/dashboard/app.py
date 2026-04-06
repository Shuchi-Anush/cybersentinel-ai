"""
CyberSentinel AI — Dashboard
Author: CyberSentinel ML-LAB

Streamlit entry point.

    streamlit run src/dashboard/app.py

Multi-page layout: pages are auto-discovered from src/dashboard/pages/.
"""

import os
import time
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
# State Fetching (Source of Truth)
# ------------------------------------------------------------------

api = get_api()

try:
    health = api.health()
    api_online = True
except Exception:
    health = {}
    api_online = False

# ------------------------------------------------------------------
# NON-BLOCKING POLLING LOOP
# ------------------------------------------------------------------

now = time.time()

if "last_poll" not in st.session_state:
    st.session_state.last_poll = now

pipeline_ready = health.get("pipeline_ready", False)
pipeline_error = health.get("pipeline_error")

if api_online and not pipeline_ready and pipeline_error is None:
    if now - st.session_state.last_poll > 2:
        st.session_state.last_poll = now
        st.rerun()

# ------------------------------------------------------------------
# STATUS MAPPING
# ------------------------------------------------------------------

if not api_online:
    pipeline_status = "🔴 Offline"
elif pipeline_error is not None:
    pipeline_status = "🔴 Error"
elif pipeline_ready:
    pipeline_status = "🟢 Online"
else:
    pipeline_status = "🟡 Loading"

meta_ready = health.get("meta_ready", False)

if not api_online:
    metadata_status = "🔴 Offline"
else:
    metadata_status = "🟢 Available" if meta_ready else "🔴 Missing"

# ------------------------------------------------------------------
# Sidebar branding
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("# 🛡️ CyberSentinel AI")
    st.caption("Intrusion Detection System")
    st.divider()

    # API connection status
    if api_online:
        st.success("API Connected", icon="✅")
    else:
        st.error("API Unreachable", icon="🔴")
        st.info(
            f"Start the API server first:\n\n"
            f"```\nuvicorn src.api.main:app --reload\n```\n\n"
            f"**Target:** `{api.base_url}`"
        )

    # Use session_state to avoid blocking time.sleep
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = now

    if st.checkbox("🔄 Auto Refresh (5s)", value=False, help="Automatically refresh the dashboard every 5 seconds."):
        if now - st.session_state.last_refresh > 5:
            st.session_state.last_refresh = now
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

if pipeline_status == "🟡 Loading":
    st.info("Model is loading in background (~40–60s)")

if pipeline_error is not None:
    st.error(f"Pipeline Error: {str(pipeline_error)[:100]}")

# Quick status metrics row
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("API Status", "🟢 Online" if api_online else "🔴 Offline")
with col2:
    st.metric("Inference Pipeline", pipeline_status)
with col3:
    try:
        models = api.get_models() if api_online else {}
        n_classes = models.get("multiclass", {}).get("num_classes", "0")
    except:
        n_classes = "N/A"
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
