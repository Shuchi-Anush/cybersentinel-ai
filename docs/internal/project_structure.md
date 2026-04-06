# CyberSentinel-AI Perfect Project Structure

This document defines the official, production-hardened structure of the CyberSentinel-AI intrusion detection system. All developers must adhere to this hierarchy to ensure system reproducibility and pipeline integrity.

## 📂 Root Directory
- `src/` - Core application logic (Modular & Testable)
- `scripts/` - Pipeline execution and automation scripts
- `configs/` - Centralized YAML configuration files
- `tests/` - Comprehensive test suite (Pytest)
- `artifacts/` - Dynamic runtime outputs (Scenarios, Reports)
- `models/` - Serialized ML artifacts (Pickles, Metadata)
- `data/` - Raw and processed datasets (Ignored by VCS)
- `dashboard/` - Real-time monitoring and threat simulation interface

---

## 🧩 Component Detail

### 1. `src/` (The Core Engine)
- **`src.core.paths`**: Central switchboard for all filesystem I/O.
- **`src.core.preprocessor`**: Pipeline-safe feature normalization and scaling.
- **`src.api`**: FastAPI implementation:
    - `main.py`: Entry point for the prediction service.
    - `schemas.py`: Data validation contracts (Pydantic).
    - `services.py`: Business logic and model orchestration.

### 2. `scripts/` (The Pipeline)
- **`train_pipeline.py`**: Automated model training with stratified splitting.
- **`inference_pipeline.py`**: Batch processing and prediction validation.
- **`scenario_extractor.py`**: Data-driven extraction of median attack signatures.
- **`scenario_validator.py`**: API-based convergence check for threat simulations.

### 3. `configs/` (The Brain)
- `data.yaml`: Dataset sources, splits, and feature definitions.
- `model.yaml`: Hyperparameters and model versioning.
- `policy.yaml`: Response mappings (ALLOW, QUARANTINE, DENY).

### 4. `artifacts/` (Outputs)
- `scenarios/candidates/`: Raw extracted attack signatures.
- `scenarios/validated/`: Confirmed threat patterns ready for dashboard injection.
- `reports/`: Execution logs and performance metrics.

---

## 🛠 Standard Execution Protocol

Always execute from the project root using the module flag:

```bash
# Training
python -m src.training.train_pipeline

# API Server
uvicorn src.api.main:app --reload

# Scenario Validation
python -m scripts.scenario_validator
```

> [!IMPORTANT]
> Never use `sys.path.append`. All imports must be absolute relative to the root.
