"""
CyberSentinel AI — API Routes
Author: CyberSentinel ML-LAB

Defines the FastAPI endpoints for inference.
Uses the InferencePipeline loaded at startup via main.py lifespan.
"""

import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.api.schemas import FlowRequest, FlowBatchRequest, PredictResponse

router = APIRouter()

# Global thread pool explicitly bounded to 4 workers to prevent process starvation
# under heavy concurrent API load mapping down to Scikit-Learn/ONNX execution.
executor = ThreadPoolExecutor(max_workers=4)


def _get_pipeline():
    """Retrieve the startup-loaded pipeline from main.py."""
    from src.api.main import pipeline

    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="InferencePipeline not loaded yet. Server is still starting.",
        )
    return pipeline


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predict policy action for a single flow",
)
async def predict_flow(request: FlowRequest):
    """
    Run the full inference cascade on a single network flow and return
    a policy decision (ALLOW / QUARANTINE / DENY).
    """
    try:
        pipe = _get_pipeline()
        loop = asyncio.get_running_loop()
        decision = await loop.run_in_executor(
            executor, pipe.predict_one, request.features
        )
        return decision.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post(
    "/predict/batch",
    response_model=List[PredictResponse],
    summary="Predict policy actions for a batch of flows",
)
async def predict_batch_flows(request: FlowBatchRequest):
    """
    Run the full inference cascade on a batch of network flows.
    Returns a list of policy decisions.
    """
    try:
        if not request.flows:
            return []

        pipe = _get_pipeline()
        df = pd.DataFrame(request.flows)
        loop = asyncio.get_running_loop()
        decisions = await loop.run_in_executor(
            executor, pipe.predict, df
        )
        return [d.to_dict() for d in decisions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction error: {str(e)}")
