# CyberSentinel-AI Production System Audit Report

This report summarizes the findings of a deep system audit conducted on the CyberSentinel-AI platform, focusing on the FastAPI backend, ML inference pipeline, and Streamlit dashboard integration.

## CRITICAL ISSUES (Must Fix Immediately)

### **1. Feature Source of Truth Divergence**
- **Issue**: The system maintains three separate "sources of truth" for the 40-feature input schema.
- **Root Cause**:
    - `MetaService` (Dashboard source) loads from `models/binary/metadata.json`.
    - `InferencePipeline` (Model input source) loads from `models/binary/features.pkl`.
    - `inference_pipeline.py` (Fallback source) references `configs/selected_features.json` in docstrings.
- **Exact File + Line**:
    - [meta_service.py:37](file:///d:/cybersentinel-ai/src/api/meta/meta_service.py#L37)
    - [inference_pipeline.py:118](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py#L118)
- **Fix**: Centralize feature list resolution. `InferencePipeline` and `MetaService` should both consume a single shared configuration object or have a validated checksum check during startup to ensure `features.pkl` and `metadata.json` are identical.

### **2. ONNX/Sklearn Redundant Binary Execution**
- **Issue**: The `predict` method executes the binary ONNX model but ignores its output trust scores, relying instead on a second Sklearn `CalibratedClassifierCV`.
- **Root Cause**: Redundant inference logic in the cascade. The ONNX output is run (`outputs_b = self._binary_sess.run(...)`) but only the binary label check is used, while actual probabilities come from the Sklearn pickle.
- **Exact File + Line**: [inference_pipeline.py:203-210](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py#L203-210)
- **Fix**: Either fully commit to ONNX (by calibrating the ONNX model at export time) or remove the redundant `_binary_sess.run` call to save CPU cycles and eliminate "score drift" potential.

---

## HIGH RISK ISSUES

### **1. Blocking Retries in Streamlit Thread**
- **Issue**: The API client uses `time.sleep` in its exponential backoff loop.
- **Potential Failure**: In Streamlit, this blocks the entire script execution for that user session. If the API is slow or transiently down, the UI will freeze for 0.5s–2s without any "Loading" indicator or ability to interrupt.
- **File**: [api_client.py:113](file:///d:/cybersentinel-ai/src/dashboard/api_client.py#L113)

### **2. Opaque Health Errors (Truncation)**
- **Issue**: Health and prediction errors are hard-truncated to 100 characters.
- **Potential Failure**: Root causes like `ONNX_RUNTIME_EXCEPTION: [Serialization]...` or `Pickle: AttributeError: Can't get attribute 'MyScaler'...` often exceed 100 characters. The user/admin will see generic prefixes instead of actionable error details.
- **File**: [main.py:106](file:///d:/cybersentinel-ai/src/api/main.py#L106) and [routes.py:37](file:///d:/cybersentinel-ai/src/api/routes.py#L37)

---

## MEDIUM / LOW ISSUES

### **1. Hardcoded Prediction Threshold**
- **Issue**: The `binary_threshold` is hardcoded to `0.3` in the `InferencePipeline` constructor, but the `predict` wrapper allows it to be passed.
- **Improvement**: Move this to `configs/training.yaml` so SOC analysts can tune sensitivity (Precision-Recall tradeoff) without code changes.
- **File**: [inference_pipeline.py:109](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py#L109)

### **2. Case-Insensitive Policy Mapping Risk**
- **Issue**: `PolicyMapper` normalizes all labels to lowercase for matching, but the multi-class labels in `metadata.json` might be mixed case (e.g. `DoS Hulk`).
- **Improvement**: Ensure labels are consistently normalized during the training phase metadata generation to avoid "Unknown Attack Type" fallbacks in the policy engine.

---

## ARCHITECTURE OBSERVATIONS

### **1. Progressive Readiness Strategy**
The use of `lifespan` in FastAPI with an `asyncio.create_task` for background model loading is highly sophisticated. It allows the API and MetaService to be "Active" instantly, while the Dashboard correctly identifies the `🟡 Loading` state. This prevents 503 errors during cold starts.

### **2. Thread Pool Management**
The explicit use of a `ThreadPoolExecutor(max_workers=4)` in `routes.py` is a strong production design. It prevents Scikit-Learn/Pandas operations from starving the Uvicorn event loop, ensuring the API remains responsive to health checks even under heavy inference load.

### **3. Cascadic Policy Mapping**
The decoupling of `PolicyMapper` from the ML model is a major design strength. It enables SOC teams to change response rules (e.g., move 'PortScan' from QUARANTINE to DENY) by simply editing a YAML file, without requiring model retraining or code deployment.
