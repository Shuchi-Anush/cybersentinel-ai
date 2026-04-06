# Phase 1 — Pre-Execution Failure Review

---

## 🔴 Critical Issues (WILL Break System)

---

### 🔴 C1 — Scenario Feature Vectors Will Return 422 Errors (Every Single One)

**Issue**: Every hardcoded scenario dict in the plan contains **wrong feature names**. The plan includes 4 features that don't exist in the selected features list, and is missing 5 features that DO exist and ARE required.

**Proof** — the actual 40 selected features (from `configs/selected_features.json`) include:

```
Active Max        ← MISSING from all 6 scenario dicts
Active Min        ← MISSING from all 6 scenario dicts
Active Std        ← MISSING from all 6 scenario dicts
Idle Std          ← MISSING from all 6 scenario dicts
```

And the scenario dicts include these features that **do NOT exist** in the selected list:

```
Fwd IAT Total              ← NOT a selected feature (will be dropped)
Bwd Packet Length Mean     ← NOT a selected feature (will be dropped)
Bwd Packet Length Std      ← NOT a selected feature (will be dropped)
Fwd Packet Length Std      ← NOT a selected feature (will be dropped)
```

**Why it breaks**: The plan assumed `_prepare_features()` silently pads missing features with 0.0. **It does not.** The actual code (line 311 of `inference_pipeline.py`):

```python
missing_cols = [f for f in self._features if f not in df.columns]
if missing_cols:
    raise HTTPException(
        status_code=422,
        detail=f"Missing {len(missing_cols)} required features: {list(missing_cols)[:5]}..."
    )
```

This raises a **422 Unprocessable Entity** for any missing feature. Since every scenario dict is missing `Active Max`, `Active Min`, `Active Std`, `Idle Std`, and in some cases `Active Mean` — **every scenario will fail with a 422 error**.

**Exact fix**: In every scenario's `features` dict:
1. **Remove** these 4 keys: `Fwd IAT Total`, `Bwd Packet Length Mean`, `Bwd Packet Length Std`, `Fwd Packet Length Std`
2. **Add** these 5 keys (use 0.0 for all — these are session activity features, zero is a valid passive-state value):

```python
"Active Max": 0.0,
"Active Min": 0.0,
"Active Std": 0.0,
"Idle Std": 0.0,
# "Active Mean" already present in plan — verify it's in every scenario
```

After fix, each scenario dict must have **exactly 41 keys** (40 selected features + the extra ones get harmlessly dropped) OR **exactly 40 keys** matching the selected features. Verify with:

```python
import json
selected = json.load(open("configs/selected_features.json"))["selected_features"]
for name, scenario in SCENARIOS.items():
    missing = set(selected) - set(scenario["features"].keys())
    extra = set(scenario["features"].keys()) - set(selected)
    assert not missing, f"{name}: missing {missing}"
```

---

### 🔴 C2 — `attack_proba` Stripped From API Response (Confirmed)

**Issue**: `PredictResponse` in `schemas.py` does not include `attack_proba`. FastAPI's `response_model` filtering silently drops any fields not in the Pydantic model. The entire Attack Probability Spectrum feature cannot work.

**Proof**: `PolicyDecision.to_dict()` produces a dict with key `attack_proba` (verified in `policy_mapper.py` line 111, line 119). But `PredictResponse` (line 30–42 of `schemas.py`) only declares: `action`, `binary_pred`, `confidence`, `attack_type`, `timestamp`, `reason`. FastAPI strips `attack_proba` before serializing.

**Fix** (matches the plan — confirmed correct):

```python
# In src/api/schemas.py, add to PredictResponse:
attack_proba: Optional[Dict[str, float]] = Field(
    None, description="Full probability distribution over attack classes"
)
```

---

### 🔴 C3 — `binary_prediction` Key Mismatch (Confirmed — Existing Bug)

**Issue**: The dashboard reads `result.get("binary_prediction", 0)` (line 104). The API returns `binary_pred`. Every single-flow prediction silently defaults to `0` (Benign) regardless of actual result.

**Proof**: `PredictResponse.binary_pred` (schemas.py line 34). `PolicyDecision.binary_pred` (policy_mapper.py line 108). Dashboard line 104: `binary_prediction` — wrong key.

**Impact**: The single-flow prediction tab has been **silently misrepresenting every attack as Benign** since it was written. The action/confidence display may still work (those keys are correct), but the "Prediction: Benign/Attack" metric is always wrong.

**Fix** (two lines in `2_Predict.py`):

```python
# Line 104:  binary_prediction → binary_pred
binary = result.get("binary_pred", 0)

# Line 274:  binary_prediction → binary_pred  
results_df[["action", "binary_pred", "confidence", "attack_type"]]
```

---

## 🟡 High-Risk Issues (May Break / Mislead)

---

### 🟡 H1 — No `try/except` in Scenario Tab → Unhandled Crash on API Error

**Issue**: The plan's scenario tab code calls `api.predict(scenario["features"])` without a `try/except` wrapper. If the API returns a non-200 HTTP status (500, 422, 503), the `api_client._post()` method raises `requests.HTTPError`, which propagates uncaught and crashes the Streamlit page with a raw Python traceback.

**Proof**: `api_client.py` line 139–140:
```python
except requests.exceptions.HTTPError as e:
    logger.error(...)
    raise  # ← re-raises, not caught
```

The existing single-flow tab (line 97) has `try/except Exception as e: st.error(...)`. The plan's scenario code does not.

**Fix**: Wrap the scenario inference block:

```python
if st.button("▶ Analyze Threat", type="primary", key="run_scenario"):
    try:
        with st.spinner("⚡ Running inference..."):
            result = api.predict(scenario["features"])
        if "error" in result:
            st.error(f"Inference failed: {result['error']}")
        else:
            parsed = _parse_result(result)
            _render_verdict(parsed)
            # ... rest of rendering ...
    except Exception as e:
        st.error(f"Scenario analysis failed: {e}")
```

---

### 🟡 H2 — Batch Tab `binary_prediction` Column → `KeyError` (Existing Bug)

**Issue**: Line 274 references `results_df[["action", "binary_prediction", "confidence", "attack_type"]]`. The API returns `binary_pred`, not `binary_prediction`. This raises `KeyError` inside the batch try/except block, showing "Batch prediction failed: ..." — the entire batch results section is broken.

**Why the plan's fix is incomplete**: The plan identifies this on line 274 but does NOT mention that the batch section code on lines 228–231 uses `results_df["action"]` which IS correct. The fix is only the one column reference on line 274.

---

### 🟡 H3 — Scenario Classification Results Are Unverified

**Issue**: The hardcoded scenario vectors are architectural guesses, not real data rows. The model may classify the "DDoS Volumetric Flood" scenario as something else entirely. The "Borderline Detection" scenario may produce a high-confidence result instead of the intended ambiguous one. If scenarios produce unexpected classifications, the demo is worse than useless — it actively undermines trust.

**Fix approach**: After implementing the code but before declaring done, run every scenario and verify classification. If any is wrong, replace its feature vector with an actual row from `merged_cleaned.csv` using:

```python
import pandas as pd
import json

df = pd.read_csv("data/processed/merged_cleaned.csv")
features = json.load(open("configs/selected_features.json"))["selected_features"]

# Get a real DDoS row:
row = df[df["Label"] == "DDoS"].iloc[0]
print({f: float(row[f]) for f in features})
```

This produces a guaranteed-correct vector. Repeat for each scenario.

---

## 🟢 Minor Improvements (Optional)

---

### 🟢 M1 — `st.progress(text=...)` Markdown Rendering

**Issue**: The plan uses markdown in `st.progress` text strings (e.g., `f"**{cls}** — {bar_val:.1%}"`). Whether `st.progress` renders markdown in the `text` parameter depends on Streamlit version. In some versions, literal `**` asterisks appear.

**Fix**: Test on your Streamlit version. If markdown doesn't render, switch to plain text:
```python
st.progress(bar_val, text=f"{cls} — {bar_val:.1%}")
```

---

### 🟢 M2 — `st.button(type="primary")` Version Compatibility

**Issue**: `type="primary"` for `st.button` was added in Streamlit 1.26.0. If the installed version is older, this raises `TypeError`.

**Fix**: Check version before shipping, or remove the `type` parameter:
```python
st.button("▶ Analyze Threat", key="run_scenario")  # safe for all versions
```

---

### 🟢 M3 — Results Vanish on Radio Button Change

**Issue**: Streamlit reruns the entire page when the user clicks a different radio option. Since results are rendered inside `if st.button(...)`, they disappear when the radio triggers a rerun (button state resets to `False`). The user must click "Analyze" again.

**Status**: This is standard Streamlit behavior, not a bug. But it can surprise users during demos. Using `st.session_state` to persist the last result would fix this, but adds complexity. Not required for P0.

---

### 🟢 M4 — Float Equality Check Lint Warning (Pre-existing)

**Issue**: Line 93 of `2_Predict.py` does `if all(v == 0.0 for v in ...)` which triggers a lint warning about float equality. This is a pre-existing issue unrelated to the plan.

**Status**: Not a runtime bug. Leave or change to `abs(v) < 1e-9` if lint cleanliness matters.

---

## ✅ Final Verdict

### ❌ NOT SAFE to implement as-is

**Confidence: 98%**

**Blocking issue**: C1 (scenario vectors missing 5 required features) will cause **every scenario to fail with a 422 error**. This is not a might-fail — it WILL fail. The `_prepare_features()` method explicitly raises on missing features. There is no fallback path.

### To make it safe

Apply these fixes in this order before writing any new code:

| Priority | Fix | Time |
|---|---|---|
| **1** | Fix scenario feature vectors: remove 4 wrong keys, add 5 missing keys | 10 min |
| **2** | Add `attack_proba` to `PredictResponse` schema | 2 min |
| **3** | Fix `binary_pred` key in lines 104 + 274 | 2 min |
| **4** | Add `try/except` around scenario inference | 2 min |
| **5** | Verify each scenario produces expected classification | 15 min |

After these 5 fixes: **safe to implement at 95% confidence**. The remaining 5% risk is scenario classification accuracy (H3), which can only be verified at runtime.

### What WAS correct in the plan

- Bug 2 analysis (attack_proba stripped) — fully confirmed
- Bug 1 analysis (binary_pred key) — fully confirmed
- `_parse_result()` logic — sound, all field accesses are defensive
- `_render_verdict()` — clean, no edge cases
- `_render_decomposition()` — progress values correctly clamped
- `_render_spectrum()` — properly guards empty attack_proba
- Tab restructuring approach — safe, no blast radius to batch tab
- No new dependencies, no new files, no structural changes — confirmed safe
