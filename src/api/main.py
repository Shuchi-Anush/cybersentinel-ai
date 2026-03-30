"""
CyberSentinel AI — API Server
Author: CyberSentinel ML-LAB

FastAPI entry point for the CyberSentinel intrusion detection system.
The InferencePipeline and MetaService are loaded once at application
startup (not lazily on the first request) to avoid latency spikes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.inference.inference_pipeline import InferencePipeline
from src.api.meta.meta_service import MetaService

logger = logging.getLogger("api")

# ------------------------------------------------------------------
# Global references — populated at startup
# ------------------------------------------------------------------
pipeline: InferencePipeline | None = None
meta_service: MetaService | None = None

PIPELINE_LOADED: bool = False
META_LOADED: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load heavy ML artifacts and metadata once at startup."""
    global pipeline, meta_service, PIPELINE_LOADED, META_LOADED

    try:
        logger.info("Loading InferencePipeline at startup…")
        pipeline = InferencePipeline()
        PIPELINE_LOADED = True
        logger.info("InferencePipeline ready.")
    except Exception as e:
        logger.error(f"Failed to load InferencePipeline: {e}")
        PIPELINE_LOADED = False

    try:
        logger.info("Loading MetaService at startup…")
        meta_service = MetaService()
        META_LOADED = True
        logger.info("MetaService ready.")
    except Exception as e:
        logger.error(f"Failed to load MetaService: {e}")
        META_LOADED = False

    yield

    # Shutdown
    pipeline = None
    meta_service = None
    PIPELINE_LOADED = False
    META_LOADED = False


app = FastAPI(
    title="CyberSentinel AI",
    description="Machine Learning Intrusion Detection System API",
    version="1.0.0",
    lifespan=lifespan,
)

# Import and mount routes AFTER app is created
from src.api.routes import router  # noqa: E402
from src.api.meta import meta_router  # noqa: E402

app.include_router(router)
app.include_router(meta_router, prefix="/meta")


@app.get("/health", summary="Health Check")
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "service": "CyberSentinel AI API",
        "pipeline_loaded": PIPELINE_LOADED,
        "meta_loaded": META_LOADED,
    }


# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
