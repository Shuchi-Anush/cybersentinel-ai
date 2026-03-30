# Dashboard Architecture Plan

## Decision: Streamlit

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Streamlit** | Already in [requirements.txt](file:///d:/cybersentinel-ai/requirements.txt) (1.55.0). Python-only — same team can maintain. Built-in charts, dataframes, live refresh. Makefile already has `make dashboard`. | Not ideal for complex multi-user auth. | **✅ Selected** |
| React/Next.js | Best for complex UIs, ATF operator console later. | Requires separate repo, npm build, different team skills. Overkill for CyberSentinel alone. | For ATF later |
| FastAPI templates (Jinja) | Same process as API. | Poor interactivity, no live charts, ugly. | ❌ Rejected |

> [!IMPORTANT]
> Streamlit runs as a **separate process** (port 8501) alongside FastAPI (port 8000). It communicates with the API via HTTP only — never imports model code directly.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                   BROWSER (:8501)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Overview │ │  Predict │ │  Eval    │ │ Policy │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘  │
│       │             │            │            │       │
│       └─────────────┴────────────┴────────────┘       │
│                         │                             │
│              HTTP (requests library)                  │
│                         │                             │
│                         ▼                             │
│              ┌──────────────────┐                     │
│              │  FastAPI (:8000) │                     │
│              │  /health         │                     │
│              │  /predict        │                     │
│              │  /predict/batch  │                     │
│              │  /meta/features  │  ← NEW read-only   │
│              │  /meta/models    │  ← NEW read-only   │
│              │  /meta/policy    │  ← NEW read-only   │
│              │  /meta/eval      │  ← NEW read-only   │
│              └────────┬─────────┘                     │
│                       │                               │
│          InferencePipeline (loaded once)               │
│          models/ configs/ data/processed/              │
└──────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
src/dashboard/                   # ← recreate this directory
├── __init__.py
├── app.py                       # Streamlit entry point (multi-page)
├── pages/
│   ├── 1_Overview.py            # health, model info, feature list
│   ├── 2_Predict.py             # single-flow + batch prediction
│   ├── 3_Evaluation.py          # metrics, confusion matrix, ROC/PR
│   └── 4_Policy.py              # active policy table, test cases
└── utils/
    └── api_client.py            # thin HTTP wrapper for FastAPI calls
```

> No other folders change. Dashboard code lives entirely inside `src/dashboard/`.

---

## API Flow

The dashboard **never imports** from `src.training`, `src.features`, `src.inference`, or `src.policy`. It only talks to FastAPI:

```
Streamlit page  ──HTTP GET──►  /health             → pipeline status
                ──HTTP GET──►  /meta/features      → feature names + importances
                ──HTTP GET──►  /meta/models         → model metadata (binary + multiclass)
                ──HTTP GET──►  /meta/policy         → deny/quarantine class lists
                ──HTTP GET──►  /meta/eval           → evaluation metrics + report
                ──HTTP POST─►  /predict             → single flow prediction
                ──HTTP POST─►  /predict/batch       → batch prediction
```

### New Endpoints Required (all read-only)

| Endpoint | Method | Returns | Source |
|---|---|---|---|
| `/meta/features` | GET | selected feature names + top-20 importances | [models/binary/metadata.json](file:///d:/cybersentinel-ai/models/binary/metadata.json) |
| `/meta/models` | GET | model type, class count, training config, data stats | [models/binary/metadata.json](file:///d:/cybersentinel-ai/models/binary/metadata.json) + [models/multiclass/metadata.json](file:///d:/cybersentinel-ai/models/multiclass/metadata.json) |
| `/meta/policy` | GET | deny/quarantine class lists, default action | [configs/policy.yaml](file:///d:/cybersentinel-ai/configs/policy.yaml) |
| `/meta/eval` | GET | metrics.json for binary + multiclass (if eval has been run) | `models/eval/summary.json` |

> [!NOTE]
> These endpoints serve static JSON already on disk — no computation.

---

## Dashboard Pages

### Phase 1 — CyberSentinel (build now)

| Page | What it shows |
|---|---|
| **Overview** | Pipeline health, model metadata, feature count, training config, class distributions |
| **Predict** | Single-flow form (fill feature values → POST /predict → show ALLOW/QUARANTINE/DENY). Batch CSV upload → POST /predict/batch → results table + download |
| **Evaluation** | Binary: accuracy, F1, ROC-AUC, confusion matrix PNG, ROC curve PNG, PR curve PNG. Multiclass: same + per-class OVA curves |
| **Policy** | Active policy table (deny list, quarantine list, default). Interactive "what-if" tester (pick attack type → show which action it maps to) |

### Phase 2 — ATF Integration (future, not built now)

| Future Page | Purpose | What it needs from ATF |
|---|---|---|
| **Trust Scores** | Per-flow trust score history + trends | ATF trust engine API |
| **Explanations** | SHAP feature attribution per prediction | SHAP integration endpoint |
| **Logs** | Zeek/Suricata log viewer, search, filter | Log ingestion API |
| **Anomaly Detection** | IsolationForest/GNN anomaly visualisation | Anomaly model endpoints |
| **Blockchain Ledger** | Audit trail of decisions | Ledger query API |
| **Network Topology** | VLAN/PEP/Join Gate visual map | Topology API |

> [!TIP]
> Phase 2 pages are added by creating new files in `src/dashboard/pages/` and extending `api_client.py`. No existing code changes.

---

## Docker Compatibility

```yaml
# docker-compose.yml (future)
services:
  api:
    build: .
    ports: ["8000:8000"]

  dashboard:
    build: .
    command: streamlit run src/dashboard/app.py --server.port 8501
    ports: ["8501:8501"]
    environment:
      - API_URL=http://api:8000
```

The dashboard reads `API_URL` from env (defaults to `http://localhost:8000` for local dev). In Docker, it resolves to the API container.

---

## Why This Design Fits ATF + CyberSentinel

| Principle | How it's satisfied |
|---|---|
| **Separation of concerns** | Dashboard never touches ML code. API is the only interface. |
| **Stability** | Adding dashboard pages doesn't modify any existing module. |
| **Extensibility** | ATF modules expose their own API endpoints → dashboard adds pages in `pages/`. |
| **Docker-ready** | Two separate services, connected by HTTP. |
| **Same-team maintainable** | Streamlit is Python — no frontend build chain needed. |
| **Replaceable** | If ATF needs React later, Streamlit can be swapped out. The API layer is framework-agnostic. |

---

## Verification Plan

### Before coding
- Confirm all 4 new `/meta/*` endpoints can be served from existing JSON files on disk

### After coding
- `make api` → API starts on :8000
- `make dashboard` → Streamlit starts on :8501
- Overview page loads model metadata via `/meta/models`
- Predict page sends a flow and gets ALLOW/DENY/QUARANTINE
- Evaluation page renders confusion matrix + ROC curve PNGs
- Policy page shows current deny/quarantine lists
