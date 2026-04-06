# Implementation Plan — Final System Hardening & Integration

This plan outlines the final steps to harden CyberSentinel-AI, ensuring strict API contract enforcement, resolving intersectional bugs, and verifying end-to-end reliability.

## User Review Required

> [!IMPORTANT]
> The `/predict` endpoint response is being reduced to exactly three fields: `action`, `confidence`, and `attack_type`. This is a breaking change for any client expecting additional metadata like `timestamp` or `reason`.
> The `/meta/eval` endpoint will now return a specific status-oriented JSON instead of the full evaluation report.

## Proposed Changes

### API (FastAPI)

#### [NEW] [services.py](file:///d:/cybersentinel-ai/src/api/services.py)
- Implement `build_response(action, confidence, attack_type=None)` with float rounding and strict field selection.

#### [MODIFY] [routes.py](file:///d:/cybersentinel-ai/src/api/routes.py)
- Replace all `to_dict()` calls with `build_response`.
- Ensure `FlowBatchRequest` results are also mapped through the builder.

#### [MODIFY] [meta_service.py](file:///d:/cybersentinel-ai/src/api/meta/meta_service.py)
- Update `get_eval` to load from `artifacts/evaluation/summary.json`.
- Implement default return `{"f1_macro": 0.0, "status": "missing"}` if file is absent or corrupted.

#### [MODIFY] [meta_routes.py](file:///d:/cybersentinel-ai/src/api/meta/meta_routes.py)
- Synchronize `/meta/eval` with the new service output.

---

### Dashboard (Streamlit)

#### [MODIFY] [3_Evaluation.py](file:///d:/cybersentinel-ai/src/dashboard/pages/3_Evaluation.py)
- Fix `NameError` for `mc_eval`.
- Add fallback warning UI for missing evaluation data.

#### [MODIFY] [2_Predict.py](file:///d:/cybersentinel-ai/src/dashboard/pages/2_Predict.py)
- Add empty input guard.
- Implement auto-wrapping for flat JSON input.
- Add strict float validation loop for features.
- Wrap all `requests` calls in `try-except` blocks.

#### [MODIFY] [app.py](file:///d:/cybersentinel-ai/src/dashboard/app.py)
- Remove `sys.path.append`.

---

### Scenario Pipeline & Logic

#### [MODIFY] [scenario_validator.py](file:///d:/cybersentinel-ai/scripts/scenario_validator.py)
- Update validation logic to correctly handle `BENIGN` labels (matching `action == "ALLOW"`).
- Ensure attack labels match and action is binary-positive (`QUARANTINE` or `DENY`).

---

### Hardening & Path Integrity

#### [MODIFY] [paths.py](file:///d:/cybersentinel-ai/src/core/paths.py)
- Verify all path constants.

#### [GLOBAL] Defensive Loading
- Wrap all `json.load`, `pd.read_csv`, and `joblib.load` calls in the codebase with `try-except` blocks.

---

### Testing

#### [NEW] [test_api_contract.py](file:///d:/cybersentinel-ai/tests/test_api_contract.py)
- Implement strict schema validation for `/predict`.

---

## Verification Plan

### Automated Tests
- Run `pytest tests/` to confirm 100% pass rate.

### Manual Verification
- **API**: Verify `/predict` and `/meta/eval` outputs via `curl`.
- **Dashboard**:
  - Test Predict page with flat JSON: `{"Flow Duration": 1.0}`.
  - Test Evaluation page without `summary.json`.
- **Scenario Pipeline**: Run `extractor` and `validator`.
