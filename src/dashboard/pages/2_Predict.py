"""
CyberSentinel AI — Dashboard: Predict Page
Author: CyberSentinel ML-LAB

Single-flow prediction form and batch CSV upload.
Data sources: GET /meta/features, POST /predict, POST /predict/batch
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from src.dashboard.api_client import get_api

st.header("🔮 Predict")

api = get_api()

if not api.is_reachable():
    st.error("⚠️ API not reachable. Run API server first.")
    st.stop()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

ACTION_COLORS = {
    "ALLOW": "🟢",
    "QUARANTINE": "🟡",
    "DENY": "🔴",
}


def action_badge(action: str) -> str:
    """Return an emoji-prefixed action string."""
    icon = ACTION_COLORS.get(action, "⚪")
    return f"{icon} **{action}**"


# Load feature list for form
features_meta = api.get_features()
feature_names: list[str] = features_meta.get("features", [])

# ------------------------------------------------------------------
# Tabs: Single Flow | Batch Upload
# ------------------------------------------------------------------

tab_single, tab_batch = st.tabs(["🎯 Single Flow", "📁 Batch Upload"])

# ==================================================================
# TAB 1 — Single Flow Prediction
# ==================================================================

with tab_single:
    st.markdown("Enter feature values for a single network flow.")

    if not feature_names:
        st.warning("No features loaded from API.")
        st.stop()

    # Feature reference in sidebar
    with st.sidebar.expander(f"📋 Features ({len(feature_names)})", expanded=False):
        for fname in feature_names:
            st.text(fname)

    # Build form with number inputs
    with st.form("predict_form", clear_on_submit=False):
        st.markdown("##### Flow Features")
        st.caption("All values default to 0.0 — fill in the relevant ones.")

        # Arrange inputs in a 3-column grid
        cols_per_row = 3
        feature_values: dict[str, float] = {}

        for i in range(0, len(feature_names), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(feature_names):
                    fname = feature_names[idx]
                    with col:
                        feature_values[fname] = st.number_input(
                            fname,
                            value=0.0,
                            format="%.4f",
                            key=f"feat_{idx}",
                        )

        submitted = st.form_submit_button("🚀 Predict", width="stretch")

    if submitted:
        # GUARD: Zero features check
        if all(v == 0.0 for v in feature_values.values()):
            st.warning("⚠️ Please enter at least one non-zero feature value to run a meaningful prediction.")
            st.stop()

        try:
            with st.spinner("🤖 Running CyberSentinel Inference..."):
                result = api.predict(feature_values)

            # --------------------------------------------------
            # SAFE PARSING (match API exactly)
            # --------------------------------------------------
            binary = result.get("binary_prediction", 0)
            confidence = result.get("confidence", 0.0)
            attack_type = result.get("attack_type", "Unknown")
            action = result.get("action", "UNKNOWN")

            # --------------------------------------------------
            # DISPLAY
            # --------------------------------------------------
            st.divider()
            st.subheader("🔍 Prediction Result")

            # 1. Metrics row
            col1, col2, col3 = st.columns(3)

            with col1:
                if binary == 0:
                    label = "Benign"
                elif binary == 1:
                    label = "Attack"
                else:
                    label = "Unknown"
                st.metric("Prediction", label)

            with col2:
                conf_val = max(0.0, min(1.0, float(confidence or 0.0)))
                conf_display = f"{conf_val:.4f}"
                st.metric("Confidence", conf_display)
                st.progress(conf_val)

            with col3:
                attack_display = attack_type if (binary == 1 and attack_type) else "—"
                st.metric("Attack Type", attack_display)

            # 2. Decision block
            st.subheader("🚦 Action Decision")

            attack_label = attack_type or "Unknown Attack"

            if action == "ALLOW":
                st.success("## 🟢 ALLOW\n**Traffic permitted**")
                st.success("**THREAT SEVERITY: LOW**")
                reason = "Binary model classified as benign."
            elif action == "QUARANTINE":
                st.warning("## 🟡 QUARANTINE\n**Isolate for inspection**")
                st.warning("**THREAT SEVERITY: MEDIUM**")
                reason = f"Attack classified as **{attack_label}** → policy applied."
            elif action == "DENY":
                st.error("## 🔴 DENY\n**Traffic blocked**")
                st.error("**THREAT SEVERITY: HIGH**")
                reason = f"Attack classified as **{attack_label}** → policy applied."
            else:
                st.info(f"## ⚪ {action}")
                reason = "Unknown classification."

            # 3. Decision Explanation
            st.markdown(f"**Reasoning:** {reason}")

            # --------------------------------------------------
            # HEURISTIC EXPLAINABILITY
            # --------------------------------------------------
            st.markdown("##### 🧠 Key Signals (Heuristic)")
            top_fs = sorted(feature_values.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            for f, v in top_fs:
                st.caption(f"**{f}** → {v:.4f}")

            # 4. Raw JSON
            with st.expander("Raw API Response"):
                st.json(result)

        except Exception as e:
            st.error(f"Prediction failed: {e}")

# ==================================================================
# TAB 2 — Batch Upload
# ==================================================================

with tab_batch:
    st.markdown("Upload a CSV file with one row per network flow.")
    st.caption(
        f"Expected columns: {', '.join(feature_names[:5])}… ({len(feature_names)} total)"
    )

    uploaded = st.file_uploader("Choose CSV", type=["csv"], key="batch_csv")

    if uploaded is not None:
        try:
            df_input = pd.read_csv(uploaded)
            
            # GUARD: Empty CSV
            if df_input.empty:
                st.error("⚠️ The uploaded CSV file is empty. Please provide a valid dataset.")
                st.stop()
            st.markdown(
                f"**Loaded:** {len(df_input)} rows × {len(df_input.columns)} columns"
            )

            # Show preview
            with st.expander("📄 Input Preview", expanded=False):
                st.dataframe(df_input.head(10), width="stretch")

            # Check for missing features
            missing = [f for f in feature_names if f not in df_input.columns]
            if missing:
                st.warning(
                    f"⚠️ {len(missing)} expected features missing from CSV "
                    f"(will be filled with 0.0): {', '.join(missing[:5])}…"
                )
            for f in missing:
                df_input[f] = 0.0
            df_input = df_input[feature_names]

            if st.button("🚀 Run Batch Prediction", width="stretch"):
                with st.spinner(f"📡 Processing {len(df_input)} flows..."):
                    flows = df_input.to_dict(orient="records")
                    results = api.predict_batch(flows)

                    # Build results DataFrame
                    results_df = pd.DataFrame(results)

                    # Summary metrics
                    st.divider()
                    st.subheader("Batch Results")

                    c1, c2, c3, c4 = st.columns(4)
                    if "action" in results_df.columns:
                        allow_count = (results_df["action"] == "ALLOW").sum()
                        quarantine_count = (results_df["action"] == "QUARANTINE").sum()
                        deny_count = (results_df["action"] == "DENY").sum()
                    else:
                        allow_count = quarantine_count = deny_count = 0

                    with c1:
                        st.metric("Total Flows", len(results_df))
                    with c2:
                        st.metric("🟢 ALLOW", allow_count)
                    with c3:
                        st.metric("🟡 QUARANTINE", quarantine_count)
                    # Distribution Chart
                    st.subheader("🚦 Action Distribution Breakdown")
                    dist_df = pd.DataFrame(
                        [
                            {"Action": "ALLOW", "Count": allow_count},
                            {"Action": "QUARANTINE", "Count": quarantine_count},
                            {"Action": "DENY", "Count": deny_count},
                        ]
                    )
                    st.bar_chart(dist_df.set_index("Action"), width="stretch")

                    # Pie Chart Breakdown
                    fig, ax = plt.subplots(figsize=(6, 4))
                    labels = ["ALLOW", "QUARANTINE", "DENY"]
                    sizes = [allow_count, quarantine_count, deny_count]
                    colors = ["#22C55E", "#EAB308", "#EF4444"]
                    
                    # Filter out zero values to avoid empty slices
                    labels = [label_name for i, label_name in enumerate(labels) if sizes[i] > 0]
                    colors = [c for i, c in enumerate(colors) if sizes[i] > 0]
                    sizes = [s for s in sizes if s > 0]

                    if sizes:
                        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=140)
                        ax.axis('equal')
                        st.pyplot(fig)
                    else:
                        st.info("No data for pie chart.")

                    # Results table
                    st.markdown("#### Tabular Output")
                    st.dataframe(
                        results_df[
                            ["action", "binary_prediction", "confidence", "attack_type"]
                        ],
                        width="stretch",
                        column_config={
                            "action": st.column_config.TextColumn(
                                "Action", width="small"
                            ),
                            "confidence": st.column_config.NumberColumn(
                                "Confidence", format="%.4f"
                            ),
                        },
                    )

                    # Download button
                    csv_data = results_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "📥 Download Results CSV",
                        data=csv_data,
                        file_name="cybersentinel_predictions.csv",
                        mime="text/csv",
                        width="stretch",
                    )

        except Exception as e:
            st.error(f"Batch prediction failed: {e}")
