# CyberSentinel AI

![Python](https://img.shields.io/badge/Python-3.10-blue)
![ML](https://img.shields.io/badge/Machine-Learning-orange)
![Docker](https://img.shields.io/badge/Docker-enabled-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Machine Learning Intrusion Detection System using CICIDS2017 dataset.

CyberSentinel detects malicious network traffic using machine learning models and provides real-time threat analytics.

---

## Features

• CIC-IDS2017 dataset integration  
• Production ML pipeline  
• Feature engineering pipeline  
• Decision Tree and Naive Bayes models  
• FastAPI inference service  
• Streamlit security dashboard  
• Docker deployment

---

## Architecture

Data Pipeline → Feature Engineering → Model Training → Evaluation → API → Dashboard

---

## Project Structure

```text
cybersentinel-ai
│
├── configs
├── data
├── docs
├── notebooks
├── scripts
├── src
├── tests
├── Dockerfile
├── Makefile
└── requirements.txt
```

---

## Dataset

This project uses the **CIC-IDS2017 dataset**.

Download manually from:

[CIC-IDS2017 Official Dataset](https://www.unb.ca/cic/datasets/ids-2017.html)

Place files inside:

data/raw/CICIDS2017/

---

## Setup

Clone repository

```bash
git clone https://github.com/Shuchi-Anush/cybersentinel-ai.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run training

```bash
python src/pipeline/pipeline_runner.py
```

---

## Roadmap

Phase 1

- Project architecture
- Repository initialization

Phase 2

- CICIDS2017 dataset loader
- Preprocessing pipeline

Phase 3

- Feature engineering
- Model training

Phase 4

- FastAPI inference service

Phase 5

- Security analytics dashboard

## License

MIT License
