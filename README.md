# CyberSentinel AI

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

---

## Dataset

This project uses the **CIC-IDS2017 dataset**.

Download manually from:

https://www.unb.ca/cic/datasets/ids-2017.html

Place files inside:

data/raw/CICIDS2017/

---

## Setup

Clone repository

git clone https://github.com/username/cybersentinel-ai.git

Install dependencies

pip install -r requirements.txt

Run training

python src/pipeline/pipeline_runner.py

---

## License

MIT License
