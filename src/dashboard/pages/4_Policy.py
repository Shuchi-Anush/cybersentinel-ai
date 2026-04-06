"""
CyberSentinel AI — Dashboard: Policy Page
Author: CyberSentinel ML-LAB

Active policy configuration and interactive what-if tester.
Data sources: GET /meta/policy, GET /meta/models (for class list)
"""

import streamlit as st
import pandas as pd
from src.dashboard.api_client import get_api

st.header("🛡️ Policy Rules")

api = get_api()

try:
    health = api.health()
    api_online = True
except Exception:
    api_online = False

if not api_online:
    st.error("⚠️ API not reachable. Run API server first.")
    st.stop()

with st.spinner("🔧 Synchronizing Global Policies..."):
    policy_data = api.get_policy()
    models = api.get_models()

deny_list = policy_data.get("deny_classes", [])
quarantine_list = policy_data.get("quarantine_classes", [])
default_action = str(policy_data.get("default_attack_action", "QUARANTINE")).upper()

# ------------------------------------------------------------------
# 0. Policy Coverage Summary
# ------------------------------------------------------------------
st.subheader("📊 Policy Coverage Summary")

mc_classes = models.get("multiclass", {}).get("attack_classes", [])
total_classes = len(mc_classes)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total Attack Classes", total_classes)
with c2:
    st.metric("🔴 Deny (Blocking)", len(deny_list))
with c3:
    st.metric("🟡 Quarantine (Isolate)", len(quarantine_list))

# Risk Distribution Chart
dist_data = pd.DataFrame([
    {"Action": "DENY", "Count": len(deny_list)},
    {"Action": "QUARANTINE", "Count": len(quarantine_list)},
    {"Action": "OTHER (Default)", "Count": max(0, total_classes - len(deny_list) - len(quarantine_list))}
])
st.bar_chart(dist_data.set_index("Action"), width="stretch")

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
mc_classes = models.get("multiclass", {}).get("attack_classes", [])
binary_classes = list(models.get("binary", {}).get("classes", {}).values())

# We want "Benign" as an option, plus all attack classes, plus an "Unknown New Attack" option
test_options = ["Benign (0)"] + sorted(mc_classes) + ["<Unknown Attack Type>"]

test_case = st.selectbox(
    "Simulate a model prediction:",
    options=test_options,
    help="Select an attack type or benign flow to see the resulting policy action.",
)

conf = st.slider("Simulated Decision Confidence:", 0.0, 1.0, 0.95)
st.caption(f"Decision confidence: {conf:.4f}")

st.markdown("**Resulting Action:**")

# --- SIMULATION LOGIC ---
final_action = "ALLOW"
if test_case == "Benign (0)":
    st.success("🟢 **ALLOW** — Traffic passes normally.")
    final_action = "ALLOW"
elif test_case in deny_list:
    st.error("🔴 **DENY** — Matched in deny list. Traffic dropped.")
    final_action = "DENY"
elif test_case in quarantine_list:
    st.warning("🟡 **QUARANTINE** — Matched in quarantine list. Traffic isolated.")
    final_action = "QUARANTINE"
else:
    final_action = default_action
    if default_action == "DENY":
        st.error("🔴 **DENY** — Not explicitly listed. Fallback to default attack action.")
    else:
        st.warning("🟡 **QUARANTINE** — Not explicitly listed. Fallback to default attack action.")

# ------------------------------------------------------------------
# 4. Strategy Insight Box
# ------------------------------------------------------------------
st.divider()
st.subheader("🧠 Strategy Insights")

if len(deny_list) < 2:
    st.warning("⚠️ **Limited high-risk coverage:** Very few classes are explicitly blocked. Monitor default actions closely.")
elif len(quarantine_list) > len(deny_list):
    st.info("ℹ️ **Conservative Strategy:** Your system prioritizes investigation (quarantine) over immediate blocking. High SOC alert volume expected.")
else:
    st.success("🎯 **Aggressive Blocking:** High-risk classes are clearly defined for immediate mitigation.")
