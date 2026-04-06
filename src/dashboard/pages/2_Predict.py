"""
CyberSentinel AI — Dashboard: Predict Page
Author: CyberSentinel ML-LAB

Threat Simulator, Single-flow prediction form, and Batch CSV upload.
Data sources: GET /meta/features, POST /predict, POST /predict/batch

IMPORTANT — Scenario feature vectors are sourced from real rows in the
training dataset (merged_cleaned.csv) to guarantee correct model output.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import ast
from src.dashboard.api_client import get_api
from src.core.paths import ARTIFACTS_DIR
from datetime import datetime
import uuid

st.header("⚡ Threat Simulator")

api = get_api()

try:
    health = api.health()
    api_online = True
except Exception:
    api_online = False

if not api_online:
    st.error("⚠️ API not reachable. Run API server first.")
    st.stop()


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

ACTION_COLORS = {
    "ALLOW": "🟢",
    "QUARANTINE": "🟡",
    "DENY": "🔴",
}

# ---------------------------------------------------------------------------
# SCENARIOS — Real rows extracted from merged_cleaned.csv.
# Feature keys exactly match configs/selected_features.json (40 features).
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {}
_scenarios_path = ARTIFACTS_DIR / "scenarios" / "validated"
FEATURE_NAMES = api.get_features().get("features", [])
FEATURE_SET = set(FEATURE_NAMES)

try:
    if _scenarios_path.exists():
        _loaded = 0
        _skipped = 0
        for _f in sorted(_scenarios_path.glob("*.json")):
            try:
                with open(_f, "r") as fh:
                    _data = json.load(fh)
                    if _data.get("validated"):
                        features_dict = _data.get("features", {})
                        
                        # Strict feature validation
                        if not features_dict or not FEATURE_SET.issubset(set(features_dict.keys())):
                            _skipped += 1
                            continue
                            
                        _label = _data.get("expected", {}).get("attack_type", "Unknown")
                        _risk = "low" if _label == "BENIGN" else ("medium" if _label == "Infiltration" else "high")
                        _risk_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(_risk, "⚪")
                        
                        _display = f"{_risk_icon}  {_label}"
                        SCENARIOS[_display] = {
                            "label": _label,
                            "risk": _risk,
                            "features": features_dict
                        }
                        _loaded += 1
                    else:
                        _skipped += 1
            except Exception:
                _skipped += 1
                continue # Skip corrupted JSON quietly per instructions
        st.caption(f"Loaded {_loaded} scenarios · Skipped {_skipped}")
except Exception as e:
    st.error(f"Failed to load dynamic scenarios: {e}")

if not SCENARIOS:
    st.error("No validated scenarios found. Run scenario pipeline.")
    st.stop()


# ------------------------------------------------------------------
# Helper: JSON extraction
# ------------------------------------------------------------------

def _safe_parse_json(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            raise ValueError("Invalid JSON or Python dict format")
    if not isinstance(parsed, dict):
        raise ValueError("Invalid JSON: root element must be a dictionary")
    return parsed

def _extract_json_features(data: dict) -> dict:
    if "features" not in data:
        raise ValueError("Missing 'features' key")
    features = data["features"]
    if not isinstance(features, dict):
        raise ValueError("Invalid features format: 'features' must be a dictionary")
        
    if not FEATURE_SET.issubset(set(features.keys())):
        raise ValueError("Invalid features schema")
        
    return features


# ------------------------------------------------------------------
# Helper: field extraction
# ------------------------------------------------------------------

def _parse_result(result: dict):
    if not result:
        return None

    trust = result.get("trust") or {}

    parsed = {
        "prediction": result.get("prediction", "Unknown"),
        "attack_type": result.get("attack_type", "Unknown"),
        "action": result.get("action", "UNKNOWN"),
        "confidence": float(result.get("confidence", 0.0)),
        "trust_score": float(trust.get("trust_score", 0.0)),
        "risk_level": str(trust.get("risk_level", "UNKNOWN")),
        "attack_proba": result.get("attack_proba", {}),
        "margin": float(result.get("margin", 0.0)),
        "incident_id": result.get("incident_id", f"ZT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"),
        "timestamp_str": datetime.utcnow().strftime("%H:%M:%S UTC")
    }

    return parsed


# ------------------------------------------------------------------
# Helper: verdict header
# ------------------------------------------------------------------

def _render_verdict(parsed: dict) -> None:
    action = parsed["action"]
    trust_score = parsed["trust_score"]
    risk_level = parsed["risk_level"]
    attack_type = parsed["attack_type"]
    incident_id = parsed["incident_id"]
    timestamp = parsed["timestamp_str"]

    # Zero-Trust Display
    trust_score = max(0.0, min(1.0, float(trust_score)))
    st.markdown(f"**Zero-Trust Identity ID:** `{incident_id}` | **Risk Level:** {risk_level}")
    st.progress(trust_score, text=f"Trust Score: {trust_score:.1%}")
    st.markdown(f"Risk Level: {risk_level}")

    if action == "ALLOW":
        st.success(f"### 🛡️ ZERO TRUST AUTH — ALLOW\nTraffic verified and within safety bounds.")
    elif action == "QUARANTINE":
        st.warning(f"### ⚠️ ZERO TRUST AUTH — QUARANTINE\nAnomaly detected ({attack_type or 'Unknown'}) — Isolated.")
    elif action == "DENY":
        st.error(f"### 🛑 ZERO TRUST AUTH — DENY\nCritical Threat Blocked: {attack_type or 'Malicious Flow'}.")
    elif action == "MONITOR":
        st.info(f"### 📡 ZERO TRUST AUTH — MONITOR\nLow-risk anomaly detected — Observation mode active.")


# ------------------------------------------------------------------
# Helper: decision decomposition
# ------------------------------------------------------------------

def _render_decomposition(parsed: dict) -> None:
    st.markdown("#### 🔬 Zero-Trust Analysis Pipeline")

    action = parsed["action"]
    prediction = parsed["prediction"]
    confidence = parsed["confidence"]
    trust_score = parsed["trust_score"]
    risk_level = parsed["risk_level"]

    # Step 1 — ML detection
    binary_label = "⚠️ ATTACK" if prediction == "Attack" else "✅ NORMAL"
    st.markdown(f"**① ML Classification** — {binary_label}")
    st.progress(confidence, text=f"Model Certainty: {confidence:.1%}")

    # Step 2 — Trust Evaluation
    st.markdown(f"**② Trust Integrity** — {risk_level} RISK")
    trust_score = max(0.0, min(1.0, float(trust_score)))
    st.progress(trust_score, text=f"Informed Trust: {trust_score:.1%}")

    # Step 3 — Policy Enforcement
    st.markdown(f"**③ Zero-Trust Authority** — {action}")
    st.progress(1.0, text="Deterministic policy enforcement")


# ------------------------------------------------------------------
# Helper: threat intelligence narrative
# ------------------------------------------------------------------

def _render_narrative(parsed: dict) -> None:
    action = parsed["action"]
    attack_type = parsed["attack_type"]
    confidence = parsed["confidence"]
    incident_id = parsed["incident_id"]

    st.markdown("#### 🧠 Threat Intelligence Summary")

    if action == "ALLOW":
        st.info(
            f"**INCIDENT:** {incident_id}  \n"
            f"**WHAT HAPPENED**  \nNetwork flow matches normal behavioral patterns.\n\n"
            f"**WHY IT WAS ALLOWED**  \nAll monitored signals fall within expected operating thresholds.\n\n"
            f"**SYSTEM DECISION**  \nTraffic allowed without escalation.\n\n"
            f"**CONFIDENCE LEVEL**  \n{confidence:.1%} — high certainty benign classification."
        )
        return

    label = attack_type or "Suspicious activity"

    st.warning(
        f"**INCIDENT:** {incident_id}  \n"
        f"**WHAT HAPPENED**  \nThe system detected behavior consistent with **{label}**.\n\n"
        f"**WHY IT WAS FLAGGED**  \nMultiple telemetry signals deviated from normal traffic patterns.\n\n"
        f"**SYSTEM DECISION**  \nAction applied: **{action}**\n\n"
        f"**CONFIDENCE LEVEL**  \n{confidence:.1%} — model strongly supports this classification.\n\n"
        f"**RECOMMENDED ACTION**  \nMonitor source activity and validate upstream protections."
    )

# ------------------------------------------------------------------
# Helper: attack probability spectrum
# ------------------------------------------------------------------

def _render_spectrum(parsed: dict) -> None:
    attack_proba = parsed["attack_proba"]
    margin = parsed["margin"]

    st.markdown("#### 📊 Attack Probability Spectrum")

    sorted_proba = sorted(attack_proba.items(), key=lambda x: x[1], reverse=True)
    display = [(cls, max(0.0, min(1.0, float(prob)))) for cls, prob in sorted_proba if prob > 0.001][:8]

    for cls, prob in display:
        st.progress(prob, text=f"{cls} — {prob:.1%}")

    if margin > 0.5:
        certainty_text = "Model certainty: HIGH — strong class discrimination."
    elif margin > 0.2:
        certainty_text = "Model certainty: MODERATE — top class leads with margin."
    else:
        certainty_text = "Model certainty: LOW — ambiguous; treat with caution."

    st.caption(f"Top-2 probability margin: **{margin:.1%}**  ·  {certainty_text}")


# ------------------------------------------------------------------
# Load feature list (used by manual + batch tabs)
# ------------------------------------------------------------------

features_meta = api.get_features()
feature_names: list[str] = features_meta.get("features", [])

# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------

tab_scenario, tab_single, tab_batch, tab_json = st.tabs([
    "⚡ Threat Simulator",
    "🔬 Manual Flow",
    "📁 Batch Analysis",
    "📡 JSON Input"
])


# ==================================================================
# TAB 1 — Threat Simulator
# ==================================================================

with tab_scenario:
    st.markdown("Select a threat scenario to run a live inference against the detection engine.")

    def clear_scenario_state():
        if "scenario_result" in st.session_state:
            del st.session_state["scenario_result"]

    scenario_names = list(SCENARIOS.keys())
    selected = st.radio(
        "Threat Scenario",
        scenario_names,
        label_visibility="collapsed",
        key="scenario_radio",
        on_change=clear_scenario_state
    )

    scenario = SCENARIOS[selected]
    risk = scenario["risk"]
    risk_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk, "⚪")
    st.caption(f"{risk_icon} {scenario['label']}")

    if st.button("▶ Analyze Threat", key="run_scenario"):
        try:
            with st.spinner("⚡ Running inference..."):
                try:
                    result = api.predict(scenario["features"])
                    st.json(result)
                except Exception:
                    st.error("API not reachable")
                    st.stop()

            if "error" in result:
                st.error(f"Inference failed: {result['error']}")
            else:
                parsed = _parse_result(result)
                st.session_state["scenario_result"] = {"parsed": parsed, "raw": result}

        except Exception as e:
            st.error(f"Scenario analysis failed: {e}")

    # Render persisted result safely
    if "scenario_result" in st.session_state:
        res = st.session_state["scenario_result"]
        parsed = res["parsed"]
        raw = res["raw"]

        st.divider()
        st.subheader("🔬 Inference Result")
        
        _render_verdict(parsed)
        st.divider()
        _render_decomposition(parsed)
        st.divider()
        _render_narrative(parsed)

        if parsed["attack_proba"]:
            st.divider()
            _render_spectrum(parsed)

        with st.expander(f"🔧 Raw API Response ({parsed['incident_id']})"):
            st.json(raw)


# ==================================================================
# TAB 2 — Manual Flow (single-flow raw form — unchanged logic)
# ==================================================================

with tab_single:
    st.markdown("Enter feature values for a single network flow.")

    if not feature_names:
        st.warning("No features loaded from API.")
        st.stop()

    with st.sidebar.expander(f"📋 Features ({len(feature_names)})", expanded=False):
        for fname in feature_names:
            st.text(fname)

    with st.form("predict_form", clear_on_submit=False):
        st.markdown("##### Flow Features")
        st.caption("All values default to 0.0 — fill in the relevant ones.")

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
        if all(abs(v) < 1e-9 for v in feature_values.values()):
            st.warning("⚠️ Please enter at least one non-zero feature value.")
            st.stop()

        try:
            with st.spinner("🤖 Running CyberSentinel Inference..."):
                try:
                    result = api.predict(feature_values)
                    st.json(result)
                except Exception:
                    st.error("API not reachable")
                    st.stop()

            parsed = _parse_result(result)
            
            st.divider()
            st.subheader("🔍 Prediction Result")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Prediction", parsed["prediction"])

            with col2:
                conf_val = max(0.0, min(1.0, float(parsed["confidence"])))
                st.metric("Confidence", f"{conf_val:.4f}")
                st.progress(conf_val)

            with col3:
                attack_display = parsed["attack_type"] if parsed["attack_type"] else "—"
                st.metric("Attack Type", attack_display)

            st.subheader("🚦 Action Decision")
            action = parsed["action"]
            risk_level = parsed["risk_level"]
            attack_label = parsed["attack_type"] or "Unknown Attack"

            if action == "ALLOW":
                st.success("## 🟢 ALLOW\n**Traffic permitted**")
                st.success("**THREAT SEVERITY: LOW**")
                reason = "Verified as within safe behavioral bounds."
            elif action == "QUARANTINE":
                st.warning("## 🟡 QUARANTINE\n**Isolate for inspection**")
                st.warning(f"**THREAT SEVERITY: {risk_level}**")
                reason = f"Anomaly detected ({attack_label}) → isolated per policy."
            elif action == "DENY":
                st.error("## 🔴 DENY\n**Traffic blocked**")
                st.error(f"**THREAT SEVERITY: {risk_level}**")
                reason = f"Critical threat identified ({attack_label}) → blocked."
            else:
                st.info(f"## ⚪ {action}")
                reason = "Unknown classification."

            st.markdown(f"**Reasoning:** {reason}")

            st.markdown("##### 🧠 Key Signals (Heuristic)")
            top_fs = sorted(feature_values.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            for f, v in top_fs:
                st.caption(f"**{f}** → {v:.4f}")

            with st.expander("Raw API Response"):
                st.json(result)

        except Exception as e:
            st.error(f"Prediction failed: {e}")


# ==================================================================
# TAB 3 — Batch Analysis (unchanged)
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

            if df_input.empty:
                st.error("⚠️ The uploaded CSV file is empty. Please provide a valid dataset.")
                st.stop()
            st.markdown(
                f"**Loaded:** {len(df_input)} rows × {len(df_input.columns)} columns"
            )

            with st.expander("📄 Input Preview", expanded=False):
                st.dataframe(df_input.head(10), width="stretch")

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

                    results_df = pd.DataFrame(results)

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
                    with c4:
                        st.metric("🔴 DENY", deny_count)

                    st.subheader("🚦 Action Distribution Breakdown")
                    dist_df = pd.DataFrame(
                        [
                            {"Action": "ALLOW", "Count": allow_count},
                            {"Action": "QUARANTINE", "Count": quarantine_count},
                            {"Action": "DENY", "Count": deny_count},
                        ]
                    )
                    st.bar_chart(dist_df.set_index("Action"), width="stretch")

                    fig, ax = plt.subplots(figsize=(6, 4))
                    labels = ["ALLOW", "QUARANTINE", "DENY"]
                    sizes = [allow_count, quarantine_count, deny_count]
                    colors = ["#22C55E", "#EAB308", "#EF4444"]

                    labels = [l for l, s in zip(labels, sizes) if s > 0]
                    colors = [c for c, s in zip(colors, sizes) if s > 0]
                    sizes = [s for s in sizes if s > 0]

                    if sizes:
                        ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=140)
                        ax.axis("equal")
                        st.pyplot(fig)
                    else:
                        st.info("No data for pie chart.")

                    st.markdown("#### Tabular Output")
                    display_cols = [c for c in ["action", "binary_pred", "confidence", "attack_type"] if c in results_df.columns]
                    st.dataframe(
                        results_df[display_cols],
                        width="stretch",
                        column_config={
                            "action": st.column_config.TextColumn("Action", width="small"),
                            "confidence": st.column_config.NumberColumn("Confidence", format="%.4f"),
                        },
                    )

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

# ==================================================================
# TAB 4 — JSON Input
# ==================================================================

with tab_json:
    st.markdown("Provide network flow features as JSON.")
    
    def clear_json_state():
        if "json_result" in st.session_state:
            del st.session_state["json_result"]
            
    input_method = st.radio(
        "Choose Input Method", 
        ["Paste JSON", "Upload .json"], 
        horizontal=True, 
        label_visibility="collapsed",
        on_change=clear_json_state
    )
    
    st.subheader("📥 Input")
    json_input = ""
    
    if input_method == "Paste JSON":
        json_input = st.text_area(
            "Paste your JSON here:",
            height=250,
            placeholder='{\n  "flow_id": "optional",\n  "features": {\n    "Flow Duration": 120.5,\n    "Total Fwd Packets": 2.0\n  }\n}',
            on_change=clear_json_state
        )
        if json_input.strip():
            st.caption("Formatted Preview:")
            try:
                parsed_preview = _safe_parse_json(json_input)
                st.code(json.dumps(parsed_preview, indent=2), language="json")
            except Exception:
                pass
    else:
        uploaded_file = st.file_uploader("Upload .json file", type=["json"], on_change=clear_json_state)
        if uploaded_file is not None:
            try:
                json_input = uploaded_file.read().decode("utf-8")
                st.caption("Formatted Preview:")
                parsed_preview = _safe_parse_json(json_input)
                st.code(json.dumps(parsed_preview, indent=2), language="json")
            except Exception as e:
                st.error(f"Failed to read file: {e}")
                
    if st.button("🚀 Analyze JSON", key="run_json"):
        clear_json_state()
        user_input = json_input.strip()
        
        if not user_input:
            st.warning("Please provide JSON input")
            st.stop()

        try:
            # 1. Parsing
            try:
                data = json.loads(user_input)
            except Exception:
                st.error("Invalid JSON format")
                st.stop()

            # 2. Auto-wrap
            if "features" not in data:
                data = {"features": data}

            # 3. Float validation loop
            if not isinstance(data["features"], dict):
                st.error("Features must be a dictionary")
                st.stop()
                
            clean = {}
            for k, v in data["features"].items():
                try:
                    clean[k] = float(v)
                except Exception:
                    st.error(f"Invalid value for {k}: {v}")
                    st.stop()
            
            features = clean

            if not features:
                st.error("❌ Features dictionary cannot be empty")
                st.stop()

            st.success("✅ JSON parsed and validated")
            
            with st.spinner("⚡ Running inference..."):
                try:
                    result = api.predict(features)
                    st.json(result)
                except Exception:
                    st.error("API not reachable")
                    st.stop()
                
            if "error" in result:
                st.error(f"Inference failed: {result['error']}")
            else:
                parsed = _parse_result(result)
                st.session_state["json_result"] = {"parsed": parsed, "raw": result}
                        
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

    # Render persisted result safely
    if "json_result" in st.session_state:
        res = st.session_state["json_result"]
        parsed = res["parsed"]
        raw = res["raw"]

        st.divider()
        st.subheader("🔬 Inference Result")
        
        _render_verdict(parsed)
        st.divider()
        _render_decomposition(parsed)
        st.divider()
        _render_narrative(parsed)

        if parsed["attack_proba"]:
            st.divider()
            _render_spectrum(parsed)
            
        with st.expander(f"🔧 Raw API Response ({parsed['incident_id']})"):
            st.json(raw)
