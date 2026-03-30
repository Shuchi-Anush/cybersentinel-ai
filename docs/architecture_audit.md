# CyberSentinel-AI — Full Architecture Audit

> Audit date: 2026-03-26 · Pre-dashboard verification

---

## 1. ✅ Correct Parts

| Area | Verdict |
|---|---|
| **Feature Selector** ([selector.py](file:///d:/cybersentinel-ai/src/features/selector.py)) | Solid 4-step cascade (Variance → Correlation → KBest → Tree). Config-driven. |
| **Preprocessor** ([preprocessor.py](file:///d:/cybersentinel-ai/src/features/preprocessor.py)) | Stratified 70/15/15 split, scaler fit-on-train-only, parquet persistence. Clean. |
| **Binary Trainer** ([binary_trainer.py](file:///d:/cybersentinel-ai/src/training/binary_trainer.py)) | SMOTE fallback to `class_weight`, val-set eval, metadata.json. Production-ready. |
| **Multiclass Trainer** ([multiclass_trainer.py](file:///d:/cybersentinel-ai/src/training/multiclass_trainer.py)) | Attack-only filtering, LabelEncoder persistence, SMOTE k-clamp. Solid design. |
| **Evaluator** ([evaluator.py](file:///d:/cybersentinel-ai/src/models/evaluator.py)) | Binary ROC/PR + multiclass OVA curves + JSON reports. Complete. |
| **Policy Mapper** ([policy_mapper.py](file:///d:/cybersentinel-ai/src/policy/policy_mapper.py)) | Config-driven deny/quarantine lists, case-insensitive matching, batch support. Clean. |
| **Inference Pipeline** ([inference_pipeline.py](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py)) | Cascaded binary→multiclass→policy. Cached singleton. Threshold-configurable. |
| **FastAPI server** ([api/main.py](file:///d:/cybersentinel-ai/src/api/main.py), [routes.py](file:///d:/cybersentinel-ai/src/api/routes.py), [schemas.py](file:///d:/cybersentinel-ai/src/api/schemas.py)) | POST /predict + /predict/batch, Pydantic v2 schemas, health endpoint. |
| **Config-driven design** | All hyperparams in [training.yaml](file:///d:/cybersentinel-ai/configs/training.yaml), policy in [policy.yaml](file:///d:/cybersentinel-ai/configs/policy.yaml). No magic numbers. |
| **Leakage prevention** | Scaler + feature selection fitted on train only. Correct. |
| **Model persistence** | `models/binary/`, `models/multiclass/` with separate `metadata.json`. Clean. |

---

## 2. ⚠ Potential Problems

### P1 · `selected_features.json` lives in TWO different path constants

> [!CAUTION]
> This is a **latent runtime bug** — it will crash if Stage 2 is run with default args after Stage 1.

| Module | Default path constant | Actual file location |
|---|---|---|
| [selector.py](file:///d:/cybersentinel-ai/src/features/selector.py#L53) | `configs/selected_features.json` ← saves here | ✅ `configs/selected_features.json` exists |
| [preprocessor.py](file:///d:/cybersentinel-ai/src/features/preprocessor.py#L66) | `data/processed/selected_features.json` ← reads here | ❌ File does NOT exist at this path |
| [inference_pipeline.py](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py#L111) | Calls `load_selected_features()` from selector → `configs/` | ✅ Works by accident |

**Impact:** Preprocessor works only because it imports `load_selected_features()` from the selector (which resolves to `configs/`), BUT the local constant `FEATURES_JSON` on line 66 points to `data/processed/` and would fail if used directly.

---

### P2 · `pipeline_runner.py` is broken and will crash

[pipeline_runner.py](file:///d:/cybersentinel-ai/src/pipeline/pipeline_runner.py) calls:
```python
model = run_training(X_train, y_train)          # OLD signature
metrics = run_evaluation(model, X_test, y_test)  # OLD signature
```

But `stage_04_training.py` now exposes `run_stage_04_training()` (no args, returns dict), and `stage_05_evaluation.py` exposes `run_stage_05_evaluation(split='test')`.

**Impact:** `make train` and `python pipeline_runner.py` will crash with `TypeError`.

---

### P3 · Dockerfile will not run inference — missing `models/` and `data/`

[Dockerfile](file:///d:/cybersentinel-ai/Dockerfile) only copies `src/` and `configs/`. It does NOT copy:
- `models/` (binary model, multiclass model, scaler, label encoder)
- `data/processed/` (parquet splits for evaluation / demo)

**Impact:** The container starts uvicorn, but the first `/predict` call loads the InferencePipeline, which calls `load_binary_model()` → `FileNotFoundError`.

---

### P4 · Scattered logging configuration — 6 separate `logging.basicConfig()` calls

Every module independently calls `logging.basicConfig()`. In Python, only the first call takes effect; subsequent calls are silently ignored. This means log format/level depends on import order — non-deterministic.

Modules: `selector.py`, `preprocessor.py`, `binary_trainer.py`, `multiclass_trainer.py`, `evaluator.py`, `inference_pipeline.py`, `policy_mapper.py`

---

### P5 · `_prepare_features()` calls `df.copy()` inside a for-loop

[inference_pipeline.py L271-273](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py#L271-L273):
```python
for col in missing_cols:
    df = df.copy()       # full copy PER missing column
    df[col] = 0.0
```
If 10 features are missing, this makes 10 full DataFrame copies. Should be a single `.copy()` before the loop.

---

### P6 · No input validation on the API `/predict` endpoint

[routes.py](file:///d:/cybersentinel-ai/src/api/routes.py) passes `request.features` directly to `predict_one()`. If an empty dict `{}` is sent, the pipeline will silently fill all 40 features with 0.0 and return a prediction — no error, no warning to the caller. This could produce misleading ALLOW decisions.

---

### P7 · API loads the inference pipeline lazily on the first request

The `predict_one()` / `predict()` module-level convenience wrappers use a `_default_pipeline` global that is instantiated lazily. This means the first API request triggers loading ~140 MB of model files, causing a multi-second latency spike. Models should be loaded at FastAPI startup via a lifespan event.

---

### P8 · No `eval/` directory in tree — evaluation has never been run on test set

`models/eval/` does not exist, meaning Stage 5 has not been executed. Binary and multiclass models were evaluated on *val* during training, but there is no held-out test-set evaluation report.

---

## 3. ❌ Architecture Violations

### V1 · Dead code: 11 empty stub files still in the tree

| File | Status |
|---|---|
| `src/config.py` | Empty (0 bytes) |
| `src/utils/logger.py` | Empty |
| `src/utils/logging_utils.py` | Empty |
| `src/utils/helpers.py` | Empty |
| `src/utils/data_utils.py` | Empty |
| `src/utils/file_utils.py` | Empty |
| `src/dashboard/app.py` | Empty |
| `src/visualization/dashboard.py` | Empty |
| `src/models/predict_model.py` | Empty |
| `src/api/api.py` | Empty (alongside the actual `main.py`) |
| `tests/test_*.py` (4 files) | All empty |

These create a false sense of completeness and confuse contributors.

---

### V2 · Duplicate config loading infrastructure

Three separate systems exist for config loading, none of which are used consistently:
1. `src/config/config_loader.py` → `load_config(name)` — **never imported by any module**
2. `src/config.py` — empty
3. Each module (selector, preprocessor, binary_trainer, multiclass_trainer, evaluator) independently opens and parses YAML

**Violation:** No single source of truth for config. A change to `training.yaml` structure could break modules individually without any shared validation.

---

### V3 · Stale legacy configs that don't match the new pipeline

| Config file | Problem |
|---|---|
| `configs/model.yaml` | References `decision_tree` and `naive_bayes` — never used by any new module |
| `configs/data.yaml` | Defines day-based `train_days` / `test_days` split — the new pipeline uses random stratified splitting instead |

These files will confuse future ATF developers trying to understand the system.

---

### V4 · `src/models/train_model.py` — legacy MLflow trainer still in tree

This 88-line file uses an entirely different pipeline (DecisionTree, PCA, `SelectKBest(k=20)`, single train/test split) and conflicts with the new modular design. It is not called by anything but imports suggest it could be.

---

### V5 · No `__init__.py` exports for `src/api/`

`src/api/__init__.py` is empty. The API package doesn't expose `app` or the router, making it difficult for other code (tests, Streamlit dashboard) to import the FastAPI app programmatically.

---

### V6 · `src/data/load_data.py` uses scenario-based split — contradicts new pipeline

The legacy data loader hardcodes Mon–Wed for train and Thu–Fri for test. The current pipeline uses `merged_cleaned.csv` with a random stratified split. Both loading strategies co-exist, creating ambiguity about which is canonical.

---

## 4. 🔧 Recommended Fixes

### Priority: CRITICAL (must fix before dashboard)

| # | Fix | Files |
|---|---|---|
| **F1** | Unify `selected_features.json` path to `data/processed/` — selector should save there, preprocessor already expects it there. Update the selector's `OUTPUT_PATH`. | `selector.py` L53 |
| **F2** | Rewrite `pipeline_runner.py` to use the new stage function signatures, or delete it and replace with a new orchestrator. | `pipeline_runner.py` |
| **F3** | Fix Dockerfile to COPY `models/` and `data/processed/` or use volume mounts. | `Dockerfile` |
| **F4** | Load InferencePipeline at FastAPI startup (lifespan event), not lazily on first request. | `api/main.py` |

### Priority: HIGH (should fix before dashboard)

| # | Fix | Files |
|---|---|---|
| **F5** | Delete all 11 empty stub files — they are dead code. | see V1 list |
| **F6** | Consolidate config loading into `src/config/config_loader.py` and have all modules import from there. Alternatively, just delete `src/config/` and `src/config.py` since each module's private `_load_config()` works fine. | `src/config/`, `src/config.py` |
| **F7** | Delete or archive `configs/model.yaml`, `configs/data.yaml`, `src/models/train_model.py`, `src/data/load_data.py` — they are stale legacy code. | see V3, V4, V6 |
| **F8** | Centralise logging: create one `src/utils/logger.py` that configures the root logger, and remove all `logging.basicConfig()` calls from individual modules. | All 7 modules |
| **F9** | Fix `_prepare_features()` copy-in-loop to a single copy before the loop. | `inference_pipeline.py` L271 |

### Priority: MEDIUM (nice-to-have before ATF)

| # | Fix | Files |
|---|---|---|
| **F10** | Add API input validation — reject empty feature dicts, return proper 422 with list of missing features. | `routes.py` |
| **F11** | Update `Makefile` targets: `train` should call the new stages, `dashboard` should use the correct entry point. | `Makefile` |
| **F12** | Run `evaluator.py` on test set to generate `models/eval/` reports before dashboard displays them. | — |
| **F13** | Write at least smoke tests for each stage in `tests/`. | `tests/` |

---

## 5. 📁 Suggested Final Folder Structure

Files/dirs marked ~~strikethrough~~ should be **deleted**. Items marked ★ are **new or moved**.

```
cybersentinel-ai/
├── configs/
│   ├── training.yaml              # feature_selection + binary + multiclass params
│   ├── policy.yaml                # ALLOW / QUARANTINE / DENY rules
│   ├── ~~model.yaml~~             # DELETE — stale legacy
│   └── ~~data.yaml~~              # DELETE — stale legacy
│
├── data/
│   ├── raw/CICIDS2017/            # original CSVs (DVC tracked)
│   └── processed/
│       ├── merged_cleaned.csv
│       ├── selected_features.json ★  ← MOVED from configs/
│       ├── X_{train,val,test}.parquet
│       ├── y_{train,val,test}_binary.parquet
│       └── y_{train,val,test}_label.parquet
│
├── models/
│   ├── scaler.pkl
│   ├── preprocessing_metadata.json
│   ├── binary/
│   │   ├── model.pkl
│   │   └── metadata.json
│   ├── multiclass/
│   │   ├── model.pkl
│   │   ├── label_encoder.pkl
│   │   └── metadata.json
│   └── eval/  ★                   ← generated by evaluator
│       ├── summary.json
│       ├── binary/ (metrics.json, roc_curve.png, …)
│       └── multiclass/ (metrics.json, roc_curves_ova.png, …)
│
├── src/
│   ├── ~~config.py~~              # DELETE — empty
│   ├── ~~config/~~                # DELETE — unused (or consolidate here)
│   │
│   ├── features/
│   │   ├── __init__.py
│   │   ├── selector.py            # Stage 1 — feature selection
│   │   ├── preprocessor.py        # Stage 2 — split + scale
│   │   └── ~~feature_engineering.py~~ # DELETE if unused
│   │
│   ├── training/
│   │   ├── __init__.py
│   │   ├── binary_trainer.py      # Stage 3
│   │   ├── multiclass_trainer.py  # Stage 4
│   │   └── ~~train_pipeline.py~~  # DELETE — stale legacy
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── evaluator.py           # Stage 5
│   │   ├── ~~evaluate.py~~        # DELETE — shim is unnecessary
│   │   ├── ~~predict_model.py~~   # DELETE — empty
│   │   └── ~~train_model.py~~     # DELETE — legacy MLflow trainer
│   │
│   ├── policy/
│   │   ├── __init__.py
│   │   └── policy_mapper.py       # Stage 6
│   │
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── inference_pipeline.py  # Stage 7
│   │   └── predictor.py           # (shim — could be merged)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI entry point
│   │   ├── routes.py              # POST /predict
│   │   ├── schemas.py             # Pydantic models
│   │   └── ~~api.py~~             # DELETE — empty
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── pipeline_runner.py     ★ REWRITE to match new API
│   │   ├── stage_01_data_ingestion.py  # legacy — mark as optional
│   │   ├── stage_02_preprocessing.py
│   │   ├── stage_03_feature_engineering.py  # legacy
│   │   ├── stage_04_training.py
│   │   └── stage_05_evaluation.py
│   │
│   ├── dashboard/                 ★ implement next
│   │   ├── __init__.py
│   │   └── app.py                 # Streamlit entry point
│   │
│   ├── ~~data/~~                  # Keep only preprocess.py shim if needed
│   │   ├── ~~load_data.py~~       # DELETE — contradicts new pipeline
│   │   └── preprocess.py          # legacy shim
│   │
│   ├── ~~utils/~~                 # DELETE entire dir — all 5 files are empty
│   └── ~~visualization/~~         # DELETE — empty dashboard.py duplicate
│
├── tests/                         # ★ needs actual test code
├── Dockerfile                     # ★ fix: COPY models/ and data/
└── Makefile                       # ★ fix: update targets
```

---

## 6. ✔ Ready for Dashboard?

### **YES — conditionally.**

The core ML pipeline (Stages 1–7) is architecturally sound, and the inference + API layers are functional.

> [!IMPORTANT]
> **You MUST fix F1 (path inconsistency) before building the dashboard**, because the dashboard will need to reload `selected_features.json` for feature-level displays, and the current dual-path will cause confusion.

> [!WARNING]
> **F2 (broken pipeline_runner) and F5 (dead stubs)** should ideally be cleaned up first to avoid the dashboard importing or displaying stale modules.

The remaining fixes (F3–F13) are important for production but do not block dashboard development.

**Recommendation:** Fix F1, F2, F5 first → then proceed with Streamlit dashboard.
