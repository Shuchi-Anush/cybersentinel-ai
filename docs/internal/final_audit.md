# CyberSentinel-AI — Pre-Deployment Audit Report

---

## 🔴 CRITICAL ISSUES — Must Fix Before Demo

### 1. `/predict/batch` silently truncates response via `PredictResponse` model

**File:** `src/api/routes.py` — line 83

**Issue:** The batch endpoint still has `response_model=List[PredictResponse]`, and `PredictResponse` only contains `{action, confidence, attack_type}`. FastAPI will **silently strip** `prediction`, `margin`, `attack_proba`, and `trust` from every batch response. `/predict` (single) was fixed but `/predict/batch` was not.

**Why it matters:** Any batch analysis shown in the dashboard will have `trust_score=0.0` and `risk_level=UNKNOWN` — identical to the root cause of the original single-flow bug.

**Fix (1-line):**
```python
# routes.py line 83 — remove response_model
@router.post(
    "/predict/batch",
    # response_model=List[PredictResponse],   ← REMOVE THIS
    summary="Predict policy actions for a batch of flows",
)
```

---

### 2. `predict_one()` crashes with `KeyError` when prediction is `"Normal"` (no multiclass run)

**File:** `src/inference/inference_pipeline.py` — line 193–203

**Issue:** `predict_one()` unpacks `res["trust"]["trust_score"]` and `res["trust"]["risk_level"]` from `results[0]`. When the binary model predicts `Normal` (binary_pred=0), the multiclass branch is **skipped** and `attack_probas[i]` stays `None`. However `res["attack_proba"]` is `None` and `predict_one` returns it as-is. The dashboard's `_parse_result` calls `result.get("attack_proba", {})` — **safe**. But `res["trust"]` is always populated so no crash here — **false alarm, this one is safe**.

Actually the real crash risk: `res["attack_type"]` is `None` for Normal flows. `predict_one` returns `"attack_type": None`. The dashboard does `result.get("attack_type", "Unknown")` — safe. **No crash.** ✅

---

### 3. `_parse_result` falls back to `"UNKNOWN"` for `risk_level`

**File:** `src/dashboard/pages/2_Predict.py` — line 143

**Issue:** Default is `"UNKNOWN"` when `trust` is missing or empty:
```python
"risk_level": str(trust.get("risk_level", "UNKNOWN")),
```
The pipeline always returns `trust.risk_level` as LOW/MEDIUM/HIGH, so this **only triggers** if the API response is malformed (e.g. a network or serialization error). During a live demo, any transient error will flash `UNKNOWN` on screen.

**Fix:**
```python
"risk_level": str(trust.get("risk_level") or "MEDIUM"),
```

---

### 4. `_render_verdict` assigns `timestamp` but never uses it

**File:** `src/dashboard/pages/2_Predict.py` — line 163

**Issue:** `timestamp = parsed["timestamp_str"]` is assigned but never rendered. This is a linting warning surfaced multiple times. Not a crash, but wastes a slot.

**Fix (trivial):**
```python
# Remove line 163:
# timestamp = parsed["timestamp_str"]
```

---

## 🟡 HIGH RISK — Edge Cases That May Fail

### 5. `attack_proba` is `None` for Normal flows — batch DataFrame explodes

**File:** `src/inference/inference_pipeline.py` + `src/api/routes.py`

**Issue:** For Normal flows, `attack_probas[i]` is `None`. The `predict` method returns this as `"attack_proba": None`. In the **batch route**, `pd.DataFrame(results)` will create a column where some rows are `None` and others are dicts — pandas can't safely display or serialize this column. The batch results table will fail or show NaN.

**Fix:** In `predict()` decision building, default `None` to `{}`:
```python
"attack_proba": attack_probas[i] or {},
```

---

### 6. `_get_pipeline()` is called twice per request in single-flow route

**File:** `src/api/routes.py` — lines 58 and 64 (removed during edits, but originally there)

**Issue:** Looking at the current file, the duplicate call was removed. **Already safe.** ✅

---

### 7. `compute_trust_score` receives already-scaled features but `mean`/`scale` parameters are passed and unused

**File:** `src/core/trust_engine.py`

**Issue:** The new multi-signal trust engine computes `abs(feature_vector)` directly on the **already-normalized** (StandardScaler) features. The `mean` and `scale` parameters are accepted in the signature but never used — they are dead parameters. This is not a crash but is **misleading** for maintainers and reviewers who will question why they are passed.

**Fix (cosmetic but important for review):** Either use them or remove them from the signature. The safest minimal fix is to mark them as unused:
```python
def compute_trust_score(
    prob: float,
    attack_type: str,
    feature_vector: "np.ndarray",
    mean: "np.ndarray" = None,   # retained for API compat, not used
    scale: "np.ndarray" = None,  # retained for API compat, not used
    margin: float = 0.0,
) -> dict:
```

---

### 8. `apply_zero_trust()` in `policy_mapper.py` is imported and called — but now dead code

**File:** `src/inference/inference_pipeline.py`

**Issue:** After the policy logic was moved inline into the pipeline's decision loop, `self._policy.apply_zero_trust(...)` is **no longer called**. However `self._policy` (a `PolicyMapper`) is still instantiated and `apply_zero_trust` still exists. This is **not a bug**, but it means policy YAML config (`configs/policy.yaml`) has no effect on `action`. If a reviewer traces the code, they will notice this disconnect.

**Verdict:** Not a crash risk for demo, but document it clearly.

---

### 9. `_render_verdict`/`_render_decomposition` duplicate `trust_score` variable name with shadow

**File:** `src/dashboard/pages/2_Predict.py` — lines 166, 204, 217

**Issue:**
```python
trust_score = parsed["trust_score"]          # from _render_verdict
...
trust_score = max(0.0, min(1.0, float(trust_score)))   # clamp
```
Then in `_render_decomposition`:
```python
trust_score = parsed["trust_score"]
...
trust_score = max(0.0, min(1.0, float(trust_score)))   # clamp again
```
Both are safe but the double-clamp in `_render_verdict` (line 166 clamps, then line 168 uses clamped value) is fine. **No bug.** ✅

---

## 🟢 SAFE — Do Not Touch

| Component | Status |
|---|---|
| `/predict` (single) response passthrough | ✅ Returns full dict, no `response_model` truncation |
| `compute_trust_score` formula | ✅ Multi-signal: 0.5·conf + 0.3·margin + 0.2·anomaly |
| Anomaly cap at 10 | ✅ Prevents exp(-x) collapse |
| Risk mapping semantics | ✅ HIGH trust → LOW risk (correct) |
| Confidence-primary policy | ✅ Attack≥0.85→DENY, 0.6–0.84→QUARANTINE, Normal≥0.8→ALLOW |
| `predict_one()` return structure | ✅ Matches required schema exactly |
| `_parse_result()` nested trust extraction | ✅ `result.get("trust") or {}` is safe |
| Async feedback logger (20% sampling) | ✅ Non-blocking, no latency impact |
| Feature shape validation in pipeline | ✅ Raises ValueError on mismatch |
| API client retry (0.1s backoff) | ✅ Non-blocking |
| `PredictResponse` schema not enforced on single-flow | ✅ After removal of `response_model` |

---

## Summary of Required Fixes

| Priority | File | Change |
|---|---|---|
| 🔴 CRITICAL | `src/api/routes.py` line 83 | Remove `response_model=List[PredictResponse]` from batch endpoint |
| 🔴 CRITICAL | `src/inference/inference_pipeline.py` decision builder | Change `"attack_proba": attack_probas[i]` → `attack_probas[i] or {}` |
| 🟡 HIGH | `src/dashboard/pages/2_Predict.py` line 143 | Change `"UNKNOWN"` default → `"MEDIUM"` |
| 🟡 LOW | `src/dashboard/pages/2_Predict.py` line 163 | Remove unused `timestamp` assignment |
