FROM python:3.10-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY src/ ./src/
COPY configs/ ./configs/

# Create runtime dirs
RUN mkdir -p models artifacts data logs

# Security: non-root user
RUN useradd -m appuser
USER appuser

ENV PYTHONPATH=/app
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]