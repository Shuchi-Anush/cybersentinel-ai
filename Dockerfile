# Stage 1: Build Dependencies
FROM python:3.10.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

# Stage 2: Hardened Runtime
FROM python:3.10.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

RUN groupadd -r appuser && useradd -r -m -g appuser appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY src/ ./src/
COPY configs/ ./configs/

RUN chown -R appuser:appuser /app /home/appuser/.local

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]