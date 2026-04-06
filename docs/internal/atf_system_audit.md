# CyberSentinel-AI (ATF): Senior Systems Architecture Audit

This document serves as the deep technical audit of the CyberSentinel-AI system, contextualized as the ML Core within the broader Adaptive Trust Framework (ATF).

## 1. Architecture Validation
The architectural separation of **Feature Engine → ML → Policy Engine** is structurally sound and enforces the Single Responsibility Principle. However, in a production ecosystem ingesting `Zeek/Suricata` logs, the current boundaries lack an asynchronous buffering/telemetry layer.

**Missing Responsibilities:**
* **Asynchronous Broker:** The ML FastAPI layer should not synchronously wait for the Feature Engine. A message broker (e.g., Kafka / Redis Streams) must exist between the Posture Agent and the Feature Engine to handle traffic bursts.
* **Separation of State:** The ML model is stateless. The Feature Engine must own the *stateful* flow aggregations (e.g., calculating `Flow Packets/s` over a sliding time window).

## 2. Imbalance Strategy (CRITICAL)
**Binary Model (SMOTE):** Acceptable. The binary decision boundary is low-resolution (Normal vs. Anomaly). SMOTE effectively hardens the perimeter here without extreme spatial distortion.

**Multiclass Model (SMOTE = DANGEROUS):** 
Generating synthetic data for 14 heavily imbalanced classes (some highly rare like `SQL Injection` or `Heartbleed`) via SMOTE in a 40-dimensional network space is mathematically unsafe. SMOTE blindly interpolates points; in network contexts, this generates "physically impossible" packet geometries, causing the RandomForest to overfit to synthetic noise.

**Recommendation:**
* **Remove SMOTE entirely for Multiclass.**
* Switch the Scikit-learn RandomForest to `class_weight="balanced_subsample"`. This utilizes the native distributions but penalizes errors on minority classes heavily during tree construction, keeping the probability distributions authentic.

## 3. Feature Engine Design
A production Feature Engine bridging Zeek/Suricata to `netrisk.json` must be a high-throughput, stateful sliding-window aggregator (e.g., Apache Flink, Faust, or structured streaming).

**Interfaces & Contracts:**
* **Input Contract:** Raw JSON streams from Zeek (`conn.log`, `http.log`).
* **State Management:** The engine must cache IPs/Ports to compute flow durations and inter-arrival times (IAT) accurately over a 5-second tumbling window.
* **Output Contract:** `netrisk.json` must be strictly enforced via Pydantic schemas. If the Feature Engine fails to compute a window, it drops the packet, it does NOT pass garbage to the ML layer.

## 4. Inference Review
**Current Flaw:** Filling missing features with `0.0` is a catastrophic failure pattern in network ML. An Inter-Arrival Time (IAT) of `0.0` implies instantaneous physical light-speed packets, which sharply violently skews the model's traversal down the Decision Trees, guaranteeing false positives.

**Correction:**
1. **Schema Rejection:** FastAPI must reject strictly missing payloads (`HTTP 422 Unprocessable Entity`).
2. **Imputation:** If imputation is absolutely mandatory for fault tolerance, do not use `0.0`. Inject the `median` value computed from the benign training distribution, mapping it safely into the "normal" behavioral cluster.

## 5. Trust Score Design
Currently utilizing raw model `predict_proba()` as "confidence." RandomForest probabilities represent the *voting fraction of trees*, which are notoriously poorly calibrated (they rapidly spike to 0.0 or 1.0 and do not represent true statistical likelihood).

**Recommendation:**
* **Calibrate the Model:** Wrap the models in Scikit-Learn’s `CalibratedClassifierCV` (Isotonic Regression) to turn tree votes into true mathematical probabilities.
* **Compound Score:** `Trust_Score = (1.0 - Binary_Attack_Prob)`. Do not use multiclass predictability for trust; use the binary model's calibrated confidence.

## 6. Policy Engine Design
The `ALLOW / QUARANTINE / DENY` paradigm is strong but requires a more hierarchical rule structure rather than flat 1-to-1 mappings.

**Suggested Strategy:**
* **Layer 1 (Global Fallback):** `If Binary_Confidence > 0.98 -> DENY` (Regardless of multiclass output).
* **Layer 2 (Signature Mapping):** Assign severity weights. `DoS Hulk (Confidence > 0.6) -> DENY`. `PortScan (Confidence > 0.5) -> QUARANTINE`.
* **Layer 3 (Rate Limiting):** A flow that bounces between `ALLOW` but yields unpredictable probabilities should automatically elevate to `QUARANTINE` for SOC review.

## 7. Explainability (SHAP)
**Is SHAP appropriate?** Yes, `TreeExplainer` is highly accurate for Random Forests.
**Should it run in real-time?** **ABSOLUTELY NOT.** SHAP calculations are CPU-intensive and will instantly destroy your ~70ms latency SLA, causing network bottlenecks.

**Implementation:**
* **API:** The `/predict` route must remain lightning fast (<15ms).
* **SHAP:** Introduce a background worker (Celery/Redis). When the Policy Engine triggers a `DENY/QUARANTINE` action, route the `netrisk.json` payload asynchronously to an `/explain` queue, compute SHAP offline, and database the telemetry for the Dashboard to render.

## 8. Repo Structure Audit
A clean MLOps repository clearly separates immutable code from mutable state.

**Ideal Structure:**
```text
├── .github/workflows/   (CI/CD)
├── configs/             (YAML limits, JSON lists)
├── deployment/          (Dockerfiles, K8s manifests)
├── src/                 (Immutable Core)
└── tests/               (Unit & Integration)
```
**NEVER Commit (Add to `.gitignore`):**
* `mlruns/` (MLflow tracking SQLite and artifacts)
* `.pkl / .onnx` models (Models belong in cloud registries/S3 or DVC, pulling upon Docker build).
* `outputs/`, `notebooks/`, and raw datasets.

## 9. Production Readiness Check
* **Scalability (🔴 Risk):** FastAPI is async, but Scikit-Learn `predict()` is CPU-bound and blocks the Python Event Loop. High traffic will cause API timeouts. *Fix:* Run inferences in a `ThreadPoolExecutor` or export the Random Forests to `ONNX` runtime for C-optimized execution.
* **Latency (🟡 Warning):** ~70ms is suitable for out-of-band monitoring but unacceptable for inline IPS (Intrusion Prevention). ONNX + removing SHAP from the hot path will lower this to ~5ms.
* **Reproducibility (🟢 Strong):** The 1-9 pipeline design strictly enforcing sequential build logic is excellent.
* **Deployment (🟢 Strong):** The UI/API isolation is highly secure.

## 10. Final Verdict
### 🔴 Critical Flaws (Must Fix Immediately)
1. **Multiclass SMOTE:** Synthesizing rare network vectors warps the mathematical boundary. Switch to `class_weight="balanced_subsample"`.
2. **0.0 Imputation:** Instantly ruins tree traversal logic. Implement Pydantic rejections or Median imputation.
3. **Blocking Async Loop:** Scikit-learn inference blocks FastAPI's loop under concurrent load. 

### 🟡 Improvements (High Impact)
1. Export `.pkl` models to `.onnx` for massive latency reductions.
2. Calibrate `predict_proba` before utilizing it as a Trust Score.
3. Offload SHAP visual explanations entirely to an async background worker.

### 🟢 What is Already Strong
1. **System Boundaries:** Eradicating ML logic from the Streamlit UI and limiting it exclusively to the FastAPI inference engine is elite-tier design.
2. **Cascaded Optimization:** The Binary-to-Multiclass pipeline isolates the False Positive tuning from the classification accuracy successfully.
3. **In-Memory Lifespans:** Pre-loading transformers and Trees into FastAPI lifespan memory guarantees horizontal scalability without I/O penalty.
