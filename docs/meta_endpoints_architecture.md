# Meta Endpoints Architecture Plan

## Core Principle

Every data source is a **static file on disk** (JSON/YAML). Endpoints serve pre-computed metadata — zero model loading, zero computation.

---

## Architecture Diagram

```
                     FastAPI (:8000)
                          │
            ┌─────────────┼──────────────┐
            │             │              │
     inference_router  meta_router    (future routers)
     prefix: /         prefix: /meta   /trust  /logs  /ledger  /anomaly
            │             │
     ┌──────┴──┐    ┌─────┴──────┐
     │ routes  │    │ meta_routes│──► MetaService (cached)
     │ .py     │    │ .py        │        │
     │         │    │            │    reads on startup:
     │ predict │    │ /features  │    ├── models/binary/metadata.json
     │ predict │    │ /models    │    ├── models/multiclass/metadata.json
     │ /batch  │    │ /policy    │    ├── models/preprocessing_metadata.json
     └─────────┘    │ /eval      │    ├── configs/policy.yaml
                    │ /config    │    ├── configs/training.yaml
                    └────────────┘    └── models/eval/summary.json (if exists)
```

---

## Decision: Service Layer + Startup Cache

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| Load files per request | Simest | Disk I/O on every call, slow | ❌ |
| **Service loaded at startup** | Single read, fast, testable | Must restart to pick up changes | **✅ Selected** |
| Background polling | Auto-updates | Complexity, threading | For ATF later |

`MetaService` is instantiated during the existing FastAPI lifespan event (alongside the InferencePipeline). All JSON/YAML is read once and cached as dicts.

---

## Folder Structure

```
src/api/
├── __init__.py
├── main.py                 # lifespan loads InferencePipeline + MetaService
├── routes.py               # /predict, /predict/batch  (unchanged)
├── schemas.py              # inference schemas  (unchanged)
└── meta/                   # ← NEW sub-package
    ├── __init__.py
    ├── meta_routes.py      # GET /meta/* endpoints
    ├── meta_schemas.py     # Pydantic response models
    └── meta_service.py     # file loading + caching logic
```

> No other folders change. [routes.py](file:///d:/cybersentinel-ai/src/api/routes.py) and [schemas.py](file:///d:/cybersentinel-ai/src/api/schemas.py) are untouched.

---

## Router Layout

```python
# main.py — mount order
app.include_router(router)                              # /predict, /predict/batch
app.include_router(meta_router, prefix="/meta")         # /meta/*

# Future ATF routers (added when modules exist):
# app.include_router(trust_router,   prefix="/trust")
# app.include_router(logs_router,    prefix="/logs")
# app.include_router(ledger_router,  prefix="/ledger")
# app.include_router(anomaly_router, prefix="/anomaly")
# app.include_router(topology_router,prefix="/topology")
```

**Naming convention:** `/{namespace}/{resource}` — flat, RESTful, no nesting beyond 2 levels.

---

## Endpoint Table

### Phase 1 — CyberSentinel (build now)

| Endpoint | Method | Source file(s) | Returns |
|---|---|---|---|
| `GET /meta/features` | GET | [models/binary/metadata.json](file:///d:/cybersentinel-ai/models/binary/metadata.json) | Feature list (40 names) + top-20 importances (binary + multiclass) |
| `GET /meta/models` | GET | [models/binary/metadata.json](file:///d:/cybersentinel-ai/models/binary/metadata.json) + [models/multiclass/metadata.json](file:///d:/cybersentinel-ai/models/multiclass/metadata.json) + [models/preprocessing_metadata.json](file:///d:/cybersentinel-ai/models/preprocessing_metadata.json) | Model type, class count, training config, data stats, split sizes |
| `GET /meta/policy` | GET | [configs/policy.yaml](file:///d:/cybersentinel-ai/configs/policy.yaml) | Deny list, quarantine list, default action |
| `GET /meta/eval` | GET | `models/eval/summary.json` (if exists) | Binary + multiclass metrics (accuracy, F1, ROC-AUC), or 404 if eval not run |
| `GET /meta/config` | GET | [configs/training.yaml](file:///d:/cybersentinel-ai/configs/training.yaml) | Feature selection + training hyperparameters |

### Response shapes

```python
# GET /meta/features
{
  "feature_count": 40,
  "features": ["Packet Length Variance", ...],
  "binary_importances": {"Packet Length Variance": 0.136, ...},  # top 20
  "multiclass_importances": {"Total Length of Fwd Packets": 0.119, ...}
}

# GET /meta/models
{
  "binary": {
    "model_type": "RandomForestClassifier",
    "classes": {"0": "Benign", "1": "Attack"},
    "training_config": {...},
    "data": {"train_rows": 1800848, "val_rows": 385896, "feature_count": 40},
    "val_metrics": {"accuracy": 0.998, "f1_weighted": 0.998, "roc_auc": 0.9999}
  },
  "multiclass": {
    "model_type": "RandomForestClassifier",
    "attack_classes": ["Bot", "DDoS", ...],    # 14 classes
    "num_classes": 14,
    "training_config": {...},
    "data": {"train_attack_rows": 298019, ...},
    "val_metrics": {"accuracy": 0.998, "f1_macro": 0.913}
  },
  "preprocessing": {
    "scaler_type": "StandardScaler",
    "split": {"train_rows": 1800848, "val_rows": 385896, "test_rows": 385896},
    "class_distribution": {"train": {"0": 1502829, "1": 298019}, ...}
  }
}

# GET /meta/policy
{
  "deny_classes": ["DDoS", "DoS Hulk", ...],
  "quarantine_classes": ["Web Attack - Brute Force", ...],
  "default_attack_action": "QUARANTINE"
}

# GET /meta/eval
{
  "binary": {"accuracy": ..., "f1_weighted": ..., "roc_auc": ...},
  "multiclass": {"accuracy": ..., "f1_macro": ...}
}
# or 404 {"detail": "Evaluation not run yet"}

# GET /meta/config
{
  "feature_selection": {"variance_threshold": 0.01, ...},
  "binary_training": {"n_estimators": 300, ...},
  "multiclass_training": {"n_estimators": 300, ...}
}
```

### Phase 2 — Future ATF namespaces

| Namespace | Purpose | Added by |
|---|---|---|
| `/trust/*` | Trust scores, history, thresholds | ATF trust engine |
| `/logs/*` | Zeek/Suricata log queries | ATF log ingestion |
| `/ledger/*` | Blockchain audit trail | ATF ledger agent |
| `/anomaly/*` | IsolationForest/GNN results | ATF anomaly module |
| `/topology/*` | VLAN/PEP/Join Gate network map | ATF topology module |
| `/explain/*` | SHAP feature attributions | ATF SHAP integration |

> Each ATF module creates its own router file in its own package. No changes to `src/api/meta/`.

---

## MetaService Design

```python
class MetaService:
    """Loads all metadata files once at startup, caches as dicts."""

    def __init__(self):
        self.binary_meta    = self._load_json(MODELS_DIR / "binary/metadata.json")
        self.multiclass_meta = self._load_json(MODELS_DIR / "multiclass/metadata.json")
        self.preprocessing   = self._load_json(MODELS_DIR / "preprocessing_metadata.json")
        self.policy          = self._load_yaml(CONFIGS_DIR / "policy.yaml")
        self.training_config = self._load_yaml(CONFIGS_DIR / "training.yaml")
        self.eval_summary    = self._load_json_optional(EVAL_DIR / "summary.json")

    def get_features(self) -> dict: ...
    def get_models(self) -> dict: ...
    def get_policy(self) -> dict: ...
    def get_eval(self) -> dict | None: ...
    def get_config(self) -> dict: ...
```

- `_load_json_optional` returns `None` if the file doesn't exist (no crash)
- All methods return plain dicts — Pydantic validation happens in the route layer
- Loaded inside the existing [lifespan()](file:///d:/cybersentinel-ai/src/api/main.py#24-34) alongside [InferencePipeline](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py#67-279)

---

## Why This Design Fits ATF + CyberSentinel

| Principle | How |
|---|---|
| **No model loading** | MetaService reads JSON/YAML only — never touches [.pkl](file:///d:/cybersentinel-ai/models/scaler.pkl) files |
| **No inference impact** | Meta routes are in a separate router, separate service object |
| **Startup cache** | Zero disk I/O after boot — fast under load |
| **Namespace isolation** | Each `/meta/*`, `/trust/*`, `/logs/*` is its own router file — no conflicts |
| **Docker-safe** | Reads from `configs/` and [models/](file:///d:/cybersentinel-ai/src/training/train_pipeline.py#154-262) which are already COPYed in Dockerfile |
| **ATF-extensible** | Adding a new namespace = one router file + one `app.include_router()` line |
| **Testable** | `MetaService` can be instantiated with mock file paths in unit tests |

---

## Implementation Sequence

1. Create `src/api/meta/meta_service.py` — file loaders + cache
2. Create `src/api/meta/meta_schemas.py` — Pydantic response models
3. Create `src/api/meta/meta_routes.py` — 5 GET endpoints
4. Create `src/api/meta/__init__.py` — export router
5. Update [src/api/main.py](file:///d:/cybersentinel-ai/src/api/main.py) — mount meta_router + load MetaService at startup
6. Verify: `py_compile` all files + test imports
