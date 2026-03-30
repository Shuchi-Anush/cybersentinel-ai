# Dashboard Implementation Plan

## Folder Structure

```
src/dashboard/
├── __init__.py
├── app.py                  # Streamlit entry point (page config + sidebar)
├── api_client.py           # HTTP wrapper for FastAPI calls
└── pages/
    ├── 1_Overview.py       # health + model metadata + feature importances
    ├── 2_Predict.py        # single-flow form + batch CSV upload
    ├── 3_Evaluation.py     # metrics cards + confusion matrix + ROC/PR
    └── 4_Policy.py         # policy table + what-if tester
```

**Future ATF pages** (added later as `5_Trust.py`, `6_SHAP.py`, etc. — zero changes to existing files).

---

## API Client

```python
# api_client.py — thin HTTP wrapper
class CyberSentinelAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url

    # GET endpoints (cached with @st.cache_data)
    def health(self) -> dict
    def get_features(self) -> dict
    def get_models(self) -> dict
    def get_policy(self) -> dict
    def get_eval(self) -> dict | None
    def get_config(self) -> dict

    # POST endpoints (never cached)
    def predict(self, features: dict) -> dict
    def predict_batch(self, flows: list[dict]) -> list[dict]
```

- `API_URL` read from `os.environ.get("API_URL", "http://localhost:8000")`
- Uses `requests` library (already in requirements.txt)
- All GET responses cached with `@st.cache_data(ttl=300)` (5 min)
- POST responses never cached

---

## Page Specs

### Page 1 — Overview

| Component | Data source | Display |
|---|---|---|
| Pipeline status | `GET /health` | Green/red indicator + uptime |
| Model summary cards | `GET /meta/models` | 2 cards: Binary (accuracy, F1, ROC-AUC) + Multiclass (accuracy, F1 macro, 14 classes) |
| Data stats | `GET /meta/models` → preprocessing | Train/val/test row counts, class distribution bar chart |
| Feature importances | `GET /meta/features` | Horizontal bar chart — top 20 features, toggle binary/multiclass |
| Training config | `GET /meta/config` | Expandable JSON viewer |

### Page 2 — Predict

| Component | Data source | Display |
|---|---|---|
| **Single flow** | `POST /predict` | Form with feature inputs (pre-filled with defaults). Submit → shows action badge (ALLOW=green, QUARANTINE=amber, DENY=red) + confidence + attack type |
| **Batch upload** | `POST /predict/batch` | CSV file uploader → results table with action column color-coded. Download results as CSV |
| Feature reference | `GET /meta/features` | Sidebar: list of expected feature names |

### Page 3 — Evaluation

| Component | Data source | Display |
|---|---|---|
| Eval status | `GET /meta/eval` | Check if eval exists (show warning if 404) |
| Binary metrics | `GET /meta/models` → val_metrics | Metric cards: accuracy, F1, precision, recall, ROC-AUC |
| Multiclass metrics | `GET /meta/models` → val_metrics | Same + per-class F1 bar chart from metadata |
| Class breakdown | `GET /meta/models` → multiclass → attack_classes | Expandable per-class precision/recall table |

> [!NOTE]
> Evaluation plots (confusion matrix PNGs, ROC curves) require a new `/meta/eval/plot/{name}` endpoint serving static files. **Deferred** — we show numeric metrics from metadata.json for now, which is already sufficient.

### Page 4 — Policy

| Component | Data source | Display |
|---|---|---|
| Policy table | `GET /meta/policy` | Table with 3 columns: Attack Class, Action, Risk Level |
| Deny list | `GET /meta/policy` → deny_classes | Red-badged list |
| Quarantine list | `GET /meta/policy` → quarantine_classes | Amber-badged list |
| What-if tester | `GET /meta/policy` + local logic | Dropdown: pick attack type → shows which action it maps to |
| Default action | `GET /meta/policy` → default_attack_action | Info box |

---

## Design Rules

| Rule | Implementation |
|---|---|
| **No ML imports** | Dashboard only imports `requests`, `streamlit`, `pandas` |
| **API_URL env var** | `os.environ.get("API_URL", "http://localhost:8000")` |
| **Docker-ready** | `command: streamlit run src/dashboard/app.py --server.port 8501` |
| **Caching** | GET metadata cached 5 min; POST never cached |
| **Error handling** | If API unreachable → show connection error banner, not crash |
| **ATF-extensible** | New pages = new files in `pages/`, no existing file changes |

---

## Implementation Sequence

1. `api_client.py` — HTTP wrapper with all 8 endpoint methods
2. [app.py](file:///d:/cybersentinel-ai/src/dashboard/app.py) — Streamlit entry point, page config, sidebar branding
3. `pages/1_Overview.py` — health + model cards + feature chart
4. `pages/2_Predict.py` — single form + batch CSV
5. `pages/3_Evaluation.py` — metrics from metadata
6. `pages/4_Policy.py` — policy table + what-if
7. Update [Makefile](file:///d:/cybersentinel-ai/Makefile) — fix `dashboard` target
8. Verify — run both servers, test all pages

---

## Verification Plan

```bash
# Terminal 1: API
venv\Scripts\uvicorn src.api.main:app --reload

# Terminal 2: Dashboard
venv\Scripts\streamlit run src/dashboard/app.py
```

- Overview page loads model metadata ✓
- Predict page sends a flow → gets ALLOW/DENY/QUARANTINE ✓
- Evaluation page shows binary + multiclass metrics ✓
- Policy page shows deny/quarantine lists ✓
