# Implementation Plan — Surgical Production Hardening

Finalize the transition of CyberSentinel-AI from "Functionally Correct" to "Production Hardened" via surgical, high-impact refinements.

## User Review Required

> [!IMPORTANT]
> **Static Mean Baseline**: If the dataset is missing, I will now return a hard-coded "Mean Baseline" for the demo payload, providing a neutral/safe input rather than random noise. This ensures the demo behavior is stable even in artifact-restricted environments.

## Proposed Changes

### 🛡️ 1. Inference Pipeline Hardening (`src/inference/`)
- **[MODIFY] [inference_pipeline.py](file:///d:/cybersentinel-ai/src/inference/inference_pipeline.py)**:
    - **Task 1**: Scan `__init__` and `predict` logic for any remaining `print` statements and replace them with `logger.debug`.
    - **Task 4**: Update `__init__` to load `self._threshold` from `os.getenv("BINARY_THRESHOLD", 0.3)`.
    - **Task 5**: Add explanatory comment: `"ONNX used for speed, sklearn model used for calibrated probabilities"`.

### 🧪 2. Payload Generator Fixes (`scripts/`)
- **[MODIFY] [generate_payload.py](file:///d:/cybersentinel-ai/scripts/generate_payload.py)**:
    - **Task 2**: 
        - Remove `random.uniform` fallback.
        - Load `models/preprocessing_metadata.json` for fallback.
        - Implement `get_fallback_payload` using a zero-value baseline or feature-neutral baseline.
    - **Task 3**: Update label sampling filters:
        - `BENIGN`: `Label == "BENIGN"`
        - `QUARANTINE`: `["PortScan", "Bot", "Infiltration", "Web Attack - Brute Force"]`
        - `ATTACK`: `["DoS slowloris", "DoS Hulk", "DDoS"]`

### 🚀 3. System Verification
- **Task 6**: Execute `python scripts/demo_runner.py` to confirm correct action mapping:
    - **BENIGN** → `ALLOW`
    - **QUARANTINE** → `QUARANTINE`
    - **ATTACK** → `DENY`

---

## Verification Plan

### Automated Checks
- `pytest` suite for regression testing.
- `demo_runner.py` for functional validation of policy actions.

### Final Readiness Check
- No `print` logs in `stdout`.
- No `random` noise in demo payloads.
- Configuration successfully picked up via `.env` or environment.
