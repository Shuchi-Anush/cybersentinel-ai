"""
CyberSentinel AI — Dashboard: Policy Page
Author: CyberSentinel ML-LAB

Active policy configuration and interactive what-if tester.
Data sources: GET /meta/policy, GET /meta/models (for class list)
"""

import streamlit as st
from src.dashboard.api_client import get_api

st.header("🛡️ Policy Rules")

api = get_api()

if not api.is_reachable():
    st.error("⚠️ API server is not reachable. Start it first.")
    st.stop()

policy_data = api.get_policy()
deny_list = policy_data.get("deny_classes", [])
quarantine_list = policy_data.get("quarantine_classes", [])
default_action = policy_data.get("default_attack_action", "QUARANTINE").upper()

# ------------------------------------------------------------------
# 1. Active Policy Lists
# ------------------------------------------------------------------

st.subheader("Active Configuration")
st.markdown("Rules map multi-class attack predictions into firewall/SOC actions.")

col_deny, col_quar = st.columns(2)

with col_deny:
    st.markdown("#### 🔴 DENY")
    st.caption("Block immediately. High impact or direct threat.")
    if deny_list:
        for c in deny_list:
            st.error(c, icon="🚨")
    else:
        st.info("No classes in deny list.")

with col_quar:
    st.markdown("#### 🟡 QUARANTINE")
    st.caption("Isolate for investigation. Lower confidence or impact.")
    if quarantine_list:
        for c in quarantine_list:
            st.warning(c, icon="⚠️")
    else:
        st.info("No classes in quarantine list.")

st.divider()

# ------------------------------------------------------------------
# 2. Default & Baseline Rules
# ------------------------------------------------------------------

st.subheader("Baseline Rules")

col_allow, col_def = st.columns(2)

with col_allow:
    st.success("🟢 **ALLOW**", icon="✅")
    st.caption(
        "Applied automatically when the binary model predicts **Benign** (0). The multi-class model is bypassed entirely."
    )

with col_def:
    icon = "🔴" if default_action == "DENY" else "🟡"
    if default_action == "DENY":
        st.error(f"{icon} **{default_action}** (Default Attack Action)", icon="🚨")
    else:
        st.warning(f"{icon} **{default_action}** (Default Attack Action)", icon="⚠️")
    st.caption(
        "Applied when an attack is detected, but its specific type is not explicitly listed in the DENY or QUARANTINE lists above."
    )

st.divider()

# ------------------------------------------------------------------
# 3. What-if Tester
# ------------------------------------------------------------------

st.subheader("🧪 What-if Tester")
st.caption(
    "Test how an incoming prediction will be handled by the current policy engine."
)

# Get all known classes for the dropdown
models = api.get_models()
mc_classes = models.get("multiclass", {}).get("attack_classes", [])
binary_classes = list(models.get("binary", {}).get("classes", {}).values())

# We want "Benign" as an option, plus all attack classes, plus an "Unknown New Attack" option
test_options = ["Benign (0)"] + sorted(mc_classes) + ["<Unknown Attack Type>"]

test_case = st.selectbox(
    "Simulate a model prediction:",
    options=test_options,
    help="Select an attack type or benign flow to see the resulting policy action.",
)

st.markdown("**Resulting Action:**")

if test_case == "Benign (0)":
    st.success("🟢 **ALLOW** — Traffic passes normally.")

elif test_case in deny_list:
    st.error("🔴 **DENY** — Matched in deny list. Traffic dropped.")

elif test_case in quarantine_list:
    st.warning("🟡 **QUARANTINE** — Matched in quarantine list. Traffic isolated.")

else:
    # Matches the default action
    if default_action == "DENY":
        st.error(
            "🔴 **DENY** — Not explicitly listed. Fallback to default attack action."
        )
    else:
        st.warning(
            "🟡 **QUARANTINE** — Not explicitly listed. Fallback to default attack action."
        )
