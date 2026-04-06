"""
CyberSentinel AI — API Server
Author: CyberSentinel ML-LAB

FastAPI entry point for the CyberSentinel intrusion detection system.
The InferencePipeline and MetaService are loaded once at application
startup (not lazily on the first request) to avoid latency spikes.
"""

import logging
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request
from src.api.meta.meta_service import MetaService
from src.inference.inference_pipeline import InferencePipeline

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load heavy ML artifacts and metadata once at startup."""
    # Initialize state
    app.state.meta_ready = False
    app.state.pipeline_ready = False
    app.state.meta_service = None
    app.state.pipeline = None
    app.state.pipeline_error = None
    app.state.pipeline_task = None

    # 1. Load MetaService (Synchronous/Lightweight)
    try:
        logger.info("Loading MetaService at startup…")
        app.state.meta_service = MetaService()
        app.state.meta_ready = True
        logger.info("MetaService ready.")
    except Exception as e:
        logger.error("Critical: MetaService failed to load: %s", e)

    # 2. Load InferencePipeline (Background/Async)
    async def load_pipeline_task():
        try:
            logger.info("Starting background load: InferencePipeline")
            
            # Use to_thread to prevent blocking the event loop during heavy load()
            temp_pipeline = InferencePipeline()
            await asyncio.to_thread(temp_pipeline.load)
            
            app.state.pipeline = temp_pipeline
            app.state.pipeline_ready = True
            logger.info("InferencePipeline ready (background load complete)")
        except Exception as ex:
            error_msg = str(ex)
            logger.error("InferencePipeline failed to load: %s", error_msg)
            logger.warning("Pipeline failed — requires restart to recover")
            app.state.pipeline = None
            app.state.pipeline_error = error_msg
            app.state.pipeline_ready = False

    # Start non-blocking task and track it
    app.state.pipeline_task = asyncio.create_task(load_pipeline_task())

    yield

    # Shutdown — Safe cancellation and awaiting
    task = getattr(app.state, "pipeline_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Pipeline loading task cancelled during shutdown.")
            raise

    app.state.pipeline = None
    app.state.meta_service = None
    app.state.meta_ready = False
    app.state.pipeline_ready = False


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
def health_check(request: Request):
    """Progressive readiness health check."""
    pipeline_ready = getattr(request.app.state, "pipeline_ready", False)
    meta_ready = getattr(request.app.state, "meta_ready", False)
    pipe_err = getattr(request.app.state, "pipeline_error", None)

    return {
        "status": "ok" if pipeline_ready else "starting",
        "meta_ready": meta_ready,
        "pipeline_ready": pipeline_ready,
        "pipeline_error": pipe_err[:500] if pipe_err else None
    }


# For local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
