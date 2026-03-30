# CyberSentinel-AI (ATF Core): Second-Pass Architectural Blueprint

*Authored by: Principal ML Architect*  
*Scope: Refining the CyberSentinel-AI standalone pipeline into the distributed Adaptive Trust Framework (ATF)*

---

## 1. 🔴 Critical Fixes (Must Implement Now)

**1. Multiclass Spatial Geometry (SMOTE Ruin)**  
SMOTE mathematically interpolates between existing samples. While acceptable for a binary plane (Normal vs. Anomaly), running SMOTE across 14 highly specialized, sparse subsets (like `SQL Injection` vs `Heartbleed`) generates "impossible" network packets in the 40-dimensional feature space. The model will overfit to non-existent synthetic physics.  
* **Action:** Immediately remove SMOTE from `multiclass_trainer.py` and replace it with `class_weight="balanced_subsample"`.

**2. Asynchronous Event-Loop Blocking in FastAPI**  
Scikit-learn’s tree traversal (`predict` / `predict_proba`) is highly structured, CPU-bound code that completely halts the Python asyncio event loop. Under concurrent ingestion requests, your API will deadlock and timeout connections.  
* **Action:** Inference wrappers must immediately be hoisted into a thread pool using `await asyncio.get_running_loop().run_in_executor(...)`.

**3. Dangerous Imputation Vectors (`0.0`)**  
Injecting `0.0` for a missing feature (e.g., `Bwd Packet Length Min` or `Flow IAT Mean`) simulates physically impossible network states (i.e., instantaneous light-speed transfer). This forces decision trees completely out of regular training splits causing deterministic False Positives.  
* **Action:** Enforce strict contract definitions via `pydantic`. The API must return an `HTTP 422 Unprocessable Entity` if structural fields are missing. If ATF flow-state dictates missing data is inevitable, you must impute utilizing the `median` derived from your exact training sets (cached in `selected_features.json`), NEVER a raw 0.0.

---

## 2. 🟡 High-Impact Improvements

**1. Calibrating the ATF Trust Score**  
Random Forest `predict_proba()` is an aggregation of absolute tree votes, not a true probabilistic likelihood. A `[0.1, 0.9]` split means 90% of trees voted "Yes", not that there is a 90% correlation with reality.  
* **Action:** Wrap the classifiers natively using Scikit-Learn's `CalibratedClassifierCV(method='isotonic')`. This converts tree voting fractions into empirically bounded, Bayesian Bayesian probabilities.

**2. Explaining Complex Boundaries (Async SHAP)**  
Deploying `TreeExplainer` on the high-speed `/predict` endpoint guarantees latency SLA failures.  
* **Action:** SHAP execution must be isolated. Plumb a Redis message queue within the API. If `Trust_Score < 0.2` (DENY/QUARANTINE triggered), dump the `netrisk.json` into the queue. A disconnected Celery worker will calculate the SHAP tensor asynchronously and update the Streamlit ledger without impacting network traffic speed.

**3. Execution Scalability (ONNX Runtime)**  
A cascaded `sklearn` prediction averages ~70ms. For line-rate IDS in a production Data Center, this is a fatal choke point.  
* **Action:** Export your serialized `.pkl` ensembles directly pipeline-to-ONNX graphs. Operating via `onnxruntime` utilizing C-level graph optimization will collapse latency down to `~2-4ms`.

---

## 3. 🟢 What is Already Strong

* **Cascaded Inference Engine:** Architecting a two-stage filter (Binary Anomaly Filter → Multiclass Classifier) is elite system design. It allows >95% of benign traffic to inherently bypass the brutal, high-depth 14-class probability extraction, preserving massive compute bandwidth.
* **Component Air-Gapping:** Banning `sklearn` and computation mechanics from the `Streamlit` dashboard enforces immaculate SoC (Separation of Concerns). The dashboard simply pulls telemetry—CyberSentinel-AI is already perfectly positioned to become an isolated, headless helm-chart microservice for the ATF.
* **Lifespan Caching Integrity:** Loading multi-gigabyte models into application memory explicitly during the FastAPI `.lifespan` effectively negates I/O cold starts, locking inference timings strictly to CPU cycles.

---

## 4. 🏗️ Updated Architecture

```text
[ Zeek / Suricata (Raw PCAP/Logs) ]
         │
         ▼
[ ATF Feature Engine ] (Apache Flink / Redis Streams)
 ├── Strict Tumbling Window Aggregators
 ├── Tracks Stateful Flows (Packets/s, Flow Durations)
 └── Casts to netrisk.json (Strict Pydantic Contract)
         │
         ▼  (CyberSentinel-AI API Boundary)
[ High-Concurrency FastAPI /predict ]
 ├── Pydantic 422 Rejection / Median Interpolation
 ├── ThreadPoolExecutor(max_workers=Logical_Cores)
         │
         ├──► [ ONNX Binary Filter (Isotonic Calibrated) ]
         │      ├── Is Benign? ──► ALLOW (Exit in ~2ms)
         │      └── Is Anomaly? ─► Proceed to Stage 2
         │
         └──► [ ONNX Multiclass Signature (Balanced Subsample) ]
                └── Returns: Class Classification + Predict Proba
         │
         ▼
[ Multi-Layer Policy Engine ]
 ├── L1: Global Threshold (>0.98 Binary Anomaly -> DENY)
 ├── L2: Signature Escalation (DDoS -> DENY, PortScan -> QUARANTINE)
 ├── L3: Temporal Velocity (Velocity tracking anomalies/sec -> QUARANTINE)
         │
         ├───► (Sync) HTTP response to ATF Agent
         ├───► (Sync) Streamlit Dashboard Ledger 
         └───► (Async Redis Queue) ──► [ Celery SHAP Worker ] ─► Dashboard Update
```

---

## 5. 🧠 Final Engineering Decisions

**Binary vs Multiclass Synthesis**  
* **Binary:** Retain SMOTE. The anomalous / benign hyperplane is geometrically simple enough that synthesis reinforces the boundary effectively without bleeding dimensionality.  
* **Multiclass:** Move strictly to `class_weight="balanced_subsample"`.  
* **Tradeoff Override:** A lower Macro F1 is mathematically and realistically correct. Enforcing equal impact mathematically via SMOTE destroys decision rules for highly prominent threat pathways to marginally compensate for rare occurrences (XSS). Do not obfuscate reality; acknowledge the imbalance explicitly.

**Trust Score Construction**  
* `ATF Trust_Score = 1.0 - CalibratedProb(Binary_Attack)`
* Do NOT merge the multiclass prediction into the quantitative trust formula. Multiclass informs the routing **action**, but the global quantitative Trust level must entirely remain calibrated off the baseline anomaly boundary.

**Feature Engine Blueprint (Crucial for ATF integration)**  
* CyberSentinel is currently stateless. Feature derivation (calculating Max Packet Lengths, Active Means, Inter-Arrival Times) requires **stateful aggregation** across disjoint packets. Your missing `ATF Feature Engine` requires a high-throughput stream processor like `Apache Flink`. It will maintain IPs/Ports in-memory over sliding temporal windows, computing the 40 feature vectors and exporting strictly formatted `netrisk.json` packets into the ML API. 

---

## 6. 🚀 Roadmap

### Phase 1: Immediate Enhancements (CyberSentinel Refinement)
1. **Model Accuracy:** Execute `multiclass_trainer.py` utilizing `class_weight="balanced"` and abandon `imblearn.SMOTE`.
2. **Resilience:** Refactor `inference_pipeline.py`. Rip out the `0.0` mappings; enforce Pydantic type safety and validation.
3. **Concurrency:** Wrap `inference_pipeline.predict()` within `asyncio` executors inside `/api/main.py` explicitly terminating unhandled loop blocks.

### Phase 2: Next (Analytics & Performance)
1. **Calibration:** Train `CalibratedClassifierCV` wrapper logic dynamically inside `binary_trainer.py` to assert verified mathematical probability accuracy. 
2. **Speed Enhancement:** Establish an ONNX pipeline script porting `.pkl` graphs to `.onnx`.
3. **Asynchronous Explainability:** Detach SHAP calculations and route them externally over Redis to a decoupled celery cluster. 

### Phase 3: The ATF Integration Phase
1. **Containerization Pipeline:** Break out CyberSentinel from local domains; formulate strict Kubernetes Helm Charts defining the Uvicorn workers logic.
2. **The Flink Feature Gateway:** Design and build the missing stateful stream aggregation Engine reading directly off `confluent/kafka` message brokers ingesting Zeek instances.
3. **Ledger Integration:** Establish historical `QUARANTINE` analysis datablocks for SOC review via your Streamlit UI.
