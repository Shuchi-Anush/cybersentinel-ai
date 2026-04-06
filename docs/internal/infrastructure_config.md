# ==========================================
# 1. .gitignore
# ==========================================
# Python leftovers
venv/
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/

# Environment
.env

# Project specific production ignores
data/
models/
artifacts/
mlruns/
logs/
outputs/

# Explicitly allow configs and code for production visibility
!configs/
!configs/*.json
!src/
!tests/
!scripts/
!docs/

# Pattern cleanup
# Removed: *.json global ignore to preserve configs
# Specific exclusions for OS/IDEs
.DS_Store
Thumbs.db
.vscode/
.idea/

# ==========================================
# 2. .dockerignore
# ==========================================
venv/
data/
models/
artifacts/
tests/
docs/
mlruns/
logs/
.git/
.github/
.pytest_cache/
__pycache__/
*.pyc
*.pyo
*.pyd
.env
Dockerfile
.dockerignore
Makefile

# ==========================================
# 3. .dvcignore
# ==========================================
# System leftovers
logs/
artifacts/
*.tmp
temp/
__pycache__/

# ==========================================
# 4. .env
# ==========================================
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
MODEL_PATH=models/model.pkl

# ==========================================
# 5. .env.example
# ==========================================
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
MODEL_PATH=models/model.pkl

# ==========================================
# 6. .gitattributes
# ==========================================
# Auto-detect text files and normalize line endings
* text=auto

# Mark binary files explicitly to prevent text-based diffing/corruption
*.pkl binary
*.onnx binary
*.msgpack binary
*.npy binary
*.npz binary

# Ensure shell scripts use LF line endings
*.sh text eol=lf

# ==========================================
# 7. Dockerfile
# ==========================================
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and configurations
COPY src/ ./src/
COPY configs/ ./configs/

# Create empty directories for runtime mounts/volumes
RUN mkdir -p models artifacts data logs

# Environment setup
ENV PYTHONPATH=/app
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Expose API port
EXPOSE 8000

# Launch FastAPI using Uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==========================================
# 8. Makefile
# ==========================================
.PHONY: install run-api run-dashboard test lint scenario clean

install:
	pip install -r requirements.txt

run-api:
	python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	python -m streamlit run dashboard/app.py

test:
	python -m pytest tests/ --tb=short

lint:
	python -m ruff check src/ scripts/ tests/

scenario:
	python -m scripts.scenario_extractor
	python -m scripts.scenario_validator

clean:
	rm -rf __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
