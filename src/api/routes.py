"""
CyberSentinel AI — API Routes
Author: CyberSentinel ML-LAB

Defines the FastAPI endpoints for inference.
Uses the InferencePipeline singleton fetched via get_pipeline().
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.api.schemas import FlowRequest as PredictRequest, FlowBatchRequest
from src.api.main import get_pipeline

router = APIRouter()
logger = logging.getLogger("api_routes")

# Bounded thread pool explicitly for high-speed ML inference
executor = ThreadPoolExecutor(max_workers=4)


@router.post("/predict", summary="Predict policy action for a single flow")
async def predict_flow(request_data: PredictRequest):
    """
    Run the full inference cascade on a single network flow.
    Returns HTTP 503 if artifacts are missing (e.g. in CI).
    """
    pipe = get_pipeline()

    try:
        logger.info("Starting single flow prediction.")
        loop = asyncio.get_running_loop()
        
        # pipe.predict_one() triggers lazy-load internally
        prediction_output = await loop.run_in_executor(
            executor, pipe.predict_one, request_data.features
        )

        # Ensure dict conversion for FastAPI response
        if hasattr(prediction_output, "__dict__") and not isinstance(prediction_output, dict):
            prediction_output = prediction_output.__dict__

        logger.info("Single flow prediction completed.")
        return prediction_output

    except RuntimeError as e:
        # Expected in CI where model loading is hard-blocked
        logger.warning(f"Prediction failed due to lazy-load block: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error during prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/batch", summary="Predict policy actions for a batch of flows")
async def predict_batch_flows(request_data: FlowBatchRequest):
    """
    Run the full inference cascade on a batch of network flows.
    Returns HTTP 503 if artifacts are missing (e.g. in CI).
    """
    pipe = get_pipeline()

    try:
        if not request_data.flows:
            return []

        logger.info(f"Starting batch prediction for {len(request_data.flows)} flows.")
        df = pd.DataFrame(request_data.flows)
        loop = asyncio.get_running_loop()
        
        # pipe.predict() triggers lazy-load internally
        decisions = await loop.run_in_executor(
            executor, pipe.predict, df
        )
        
        logger.info("Batch prediction completed.")
        return decisions

    except RuntimeError as e:
        # Expected in CI where model loading is hard-blocked
        logger.warning(f"Batch prediction failed due to lazy-load block: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error during batch prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction error: {str(e)}")
