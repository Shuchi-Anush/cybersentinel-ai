<!-- markdownlint-disable MD033 -->
<!-- markdownlint-disable MD045 -->

# 🛡️ CyberSentinel-AI

<p align="center">
  <img src="docs/assets/banner.png" alt="CyberSentinel Banner" width="100%">
</p>

<p align="center">
  <b>Zero-Trust Intrusion Detection & Decision System</b><br>
  <sub>From Raw Network Traffic → Intelligent Security Actions in Real-Time</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge">
  <img src="https://img.shields.io/badge/FastAPI-High%20Performance-teal?style=for-the-badge">
  <img src="https://img.shields.io/badge/ML-End--to--End-green?style=for-the-badge">
  <img src="https://img.shields.io/badge/Zero--Trust-Enabled-red?style=for-the-badge">
</p>

---

## ⚡ 5-Second Overview

CyberSentinel-AI is not just an IDS.

It is a **Zero-Trust Decision Engine** that converts network flows into:

🟢 ALLOW  🟡 QUARANTINE  🔴 DENY

— automatically, instantly, and intelligently.

---

## 🚨 Problem

Traditional IDS systems:

- Detect threats but ❌ don’t enforce decisions  
- Fail against ❌ zero-day attacks  
- Require ❌ manual intervention  
- Cause ❌ alert fatigue  

---

## 💡 Solution

CyberSentinel-AI introduces a **closed-loop security system**:

Detection → Trust Evaluation → Policy Enforcement → Action

---

## 🚀 Key Differentiation

| Capability | Typical ML Project | CyberSentinel-AI |
| ----------- | ----------------- | ------------------ |
| Scope | Model only | Full system |
| Output | Prediction | Decision + Action |
| Intelligence | Static | Context-aware |
| Runtime | Notebook | API + Dashboard |
| Security | Detection | Zero-Trust Enforcement |

---

## 🏛️ Architecture

<p align="center">
  <img src="docs/assets/architecture.png" width="85%">
</p>

---

## 🧠 Core Pipeline

Network Flow Input  
↓  
Feature Validation (40 Features)  
↓  
Binary Classifier (Benign / Attack)  
↓  
Multi-class Classifier (Attack Type)  
↓  
Trust Engine (multi-signal)  
↓  
Policy Engine  
↓  
Final Decision → ALLOW / QUARANTINE / DENY  

<p align="center">
  <img src="docs/assets/pipeline.png" width="85%">
</p>

---

## 🧠 Zero-Trust Engine

### 🔬 Trust Score Formula

Trust Score = 0.5 × Confidence  
      + 0.3 × Margin  
      + 0.2 × Anomaly Signal  

### 📊 Risk Mapping

| Trust Score | Risk Level |
| ----------- | ---------- |
| ≥ 0.70 | 🟢 LOW |
| 0.40 – 0.69 | 🟡 MEDIUM |
| < 0.40 | 🔴 HIGH |

---

## 🛡️ Policy Engine (Decision Layer)

| Prediction | Confidence | Action | Risk |
| ---------- | ---------- | ------ | ---- |
| Attack | ≥ 0.85 | 🔴 DENY | HIGH |
| Attack | 0.60–0.84 | 🟡 QUARANTINE | HIGH |
| Attack | < 0.60 | 🟡 QUARANTINE | MEDIUM |
| Normal | ≥ 0.80 | 🟢 ALLOW | LOW |
| Normal | < 0.80 | 🟡 QUARANTINE | MEDIUM |

---

## 🖥️ Dashboard (SOC Interface)

Run:

streamlit run src/dashboard/app.py

### Features

- ⚡ Threat Simulator  
- 🔬 Manual flow testing  
- 📁 Batch CSV analysis  
- 📡 JSON input support  
- 📊 Probability visualization  
- 🧠 Explainable decisions  

<p align="center">
  <img src="docs/assets/predict.png" width="80%">
</p>

---

## 🔌 API Layer

Run:

uvicorn src.api.main:app --reload

### Endpoints

| Endpoint | Description |
| -------- | ----------- |
| /predict | Single flow decision |
| /predict/batch | Batch decisions |
| /meta/features | Feature schema |
| /meta/models | Model metadata |
| /meta/policy | Policy rules |
| /health | Health check |

---

## 📊 Example Response

{
  "prediction": "Attack",
  "attack_type": "DDoS",
  "action": "DENY",
  "confidence": 0.9985,
  "margin": 0.91,
  "attack_proba": {
    "DDoS": 0.998,
    "PortScan": 0.001
  },
  "trust": {
    "trust_score": 0.94,
    "risk_level": "HIGH"
  }
}

---

## 📁 Project Structure

cybersentinel-ai/  
├── src/  
│   ├── api/  
│   ├── core/  
│   ├── inference/  
│   ├── dashboard/  
├── configs/  
├── artifacts/  
├── models/ (ignored)  
├── data/ (ignored)  
├── docs/  

---

## 🎯 Scenario Pipeline

python -m scripts.scenario_extractor  
python -m scripts.scenario_validator  

✔ Data-driven  
✔ No hardcoding  
✔ Model validated  

---

## 🧪 Testing

pytest tests/ --tb=short  

---

## 🐳 Docker

docker build -t cybersentinel-ai .  
docker run -p 8000:8000 cybersentinel-ai  

---

## 🔐 Design Principles

- Modular architecture  
- Config-driven system  
- No hardcoded paths  
- Production-first design  
- Explainable AI  

---

## 🚀 Key Insight

Prediction → Trust → Decision → Action

---

## 👨‍💻 Author

Shuchi Anush S  
<https://github.com/Shuchi-Anush>  

---

## 📜 License

MIT License  

---

## 🏁 Status

✅ Production Ready
