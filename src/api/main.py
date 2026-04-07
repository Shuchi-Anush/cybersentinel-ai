"""
CyberSentinel AI — API Server
Author: CyberSentinel ML-LAB

FastAPI entry point for the CyberSentinel intrusion detection system.
The InferencePipeline is loaded lazily on the first prediction request.
Importing this module NEVER touches the filesystem or loads models.
"""

import logging
from fastapi import FastAPI
from src.api.meta.meta_service import MetaService
from src.inference.inference_pipeline import InferencePipeline

logger = logging.getLogger("api")

# ---------------------------------------------------------------------------
# Lazy pipeline singleton — populated on first /predict call, never at import
# ---------------------------------------------------------------------------

_pipeline: InferencePipeline | None = None


def get_pipeline() -> InferencePipeline:
    """Return the process-scoped pipeline singleton, loading on first call."""
    global _pipeline
    if _pipeline is None:
        _pipeline = InferencePipeline()
    return _pipeline


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CyberSentinel AI",
    description="Machine Learning Intrusion Detection System API",
    version="1.0.0",
)

# Import and mount routes AFTER app is created
from src.api.routes import router      # noqa: E402
from src.api.meta import meta_router   # noqa: E402

app.include_router(router)
app.include_router(meta_router, prefix="/meta")


@app.get("/health", summary="Health Check")
def health_check() -> dict:
    """
    Lightweight health check.
    
    Returns 'ok' always — pipeline_ready reflects whether the pipeline 
    is instantiated AND loaded. 
    
    STRICT RULE: MUST NOT trigger load().
    """
    return {
        "status": "ok",
        "pipeline_ready": (_pipeline is not None and _pipeline._loaded)
    }


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
