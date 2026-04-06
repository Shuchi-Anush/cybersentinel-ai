"""
CyberSentinel AI — API Routes
Author: CyberSentinel ML-LAB

Defines the FastAPI endpoints for inference.
Uses the InferencePipeline loaded at startup via main.py lifespan.
"""

import pandas as pd
from fastapi import APIRouter, HTTPException

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from src.api.schemas import FlowRequest as PredictRequest, FlowBatchRequest
from fastapi import Request

router = APIRouter()
logger = logging.getLogger("api_routes")

# Global thread pool explicitly bounded to 4 workers to prevent process starvation
# under heavy concurrent API load mapping down to Scikit-Learn/ONNX execution.
executor = ThreadPoolExecutor(max_workers=4)


def _get_pipeline(request: Request):
    """Retrieve the startup-loaded pipeline from app state."""
    # Strict Guard: check for error first
    pipe_err = getattr(request.app.state, "pipeline_error", None)
    if pipe_err:
        logger.error(f"Prediction blocked: Pipeline failed to load previously: {pipe_err}")
        raise HTTPException(
            status_code=500,
            detail=f"Model failed to load: {pipe_err[:500]}"
        )

    pipe = getattr(request.app.state, "pipeline", None)
    if pipe is None:
        logger.warning("Prediction requested but pipeline still loading.")
        raise HTTPException(
            status_code=503,
            detail="Model loading in progress. Retry shortly.",
        )
    return pipe


@router.post(
    "/predict",
    summary="Predict policy action for a single flow",
)
async def predict_flow(request_data: PredictRequest, request: Request):
    """
    Run the full inference cascade on a single network flow and return
    a policy decision (ALLOW / QUARANTINE / DENY).
    """
    # We call _get_pipeline at the start to ensure 500 (error) or 503 (loading)
    pipe = _get_pipeline(request)

    try:
        logger.info("Starting single flow prediction.")
        loop = asyncio.get_running_loop()
        prediction_output = await loop.run_in_executor(
            executor, pipe.predict_one, request_data.features
        )
        
        # Guard for object vs dict (Requirement 8)
        if hasattr(prediction_output, "__dict__") and not isinstance(prediction_output, dict):
            prediction_output = prediction_output.__dict__
        logger.info("Single flow prediction completed.")
        return prediction_output
    except HTTPException:
        logger.error("HTTPException during single flow prediction.")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during single flow prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post(
    "/predict/batch",
    summary="Predict policy actions for a batch of flows",
)
async def predict_batch_flows(request_data: FlowBatchRequest, request: Request):
    """
    Run the full inference cascade on a batch of network flows.
    Returns a list of policy decisions.
    """
    # We call _get_pipeline at the start to ensure 500 (error) or 503 (loading)
    pipe = _get_pipeline(request)

    try:
        if not request_data.flows:
            return []

        logger.info(f"Starting batch prediction for {len(request_data.flows)} flows.")
        df = pd.DataFrame(request_data.flows)
        loop = asyncio.get_running_loop()
        decisions = await loop.run_in_executor(
            executor, pipe.predict, df
        )
        logger.info("Batch prediction completed.")
        return decisions
    except HTTPException:
        logger.error("HTTPException during batch prediction.")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during batch prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction error: {str(e)}")
