# Stage 1: Build Dependencies
FROM python:3.10.11-slim AS builder

WORKDIR /build
COPY requirements_min.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements_min.txt

# Stage 2: Runtime
FROM python:3.10.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

RUN groupadd -r appuser && useradd -r -m -g appuser appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local

# ✅ REQUIRED FILES
COPY src/ ./src/
COPY configs/ ./configs/
COPY models/ ./models/

RUN chown -R appuser:appuser /app /home/appuser/.local

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000}"]