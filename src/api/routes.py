"""
CyberSentinel AI — API Routes
Author: CyberSentinel ML-LAB

Defines the FastAPI endpoints for inference.
"""
import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import List

from src.api.schemas import FlowRequest, FlowBatchRequest, PredictResponse
from src.inference import predict_one, predict

router = APIRouter()

@router.post("/predict", response_model=PredictResponse, summary="Predict policy action for a single flow")
def predict_flow(request: FlowRequest):
    """
    Run the full inference cascade on a single network flow and return
    a policy decision (ALLOW / QUARANTINE / DENY).
    """
    try:
        decision = predict_one(request.features)
        # Convert PolicyDecision dataclass to dict for Pydantic
        return decision.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/batch", response_model=List[PredictResponse], summary="Predict policy actions for a batch of flows")
def predict_batch_flows(request: FlowBatchRequest):
    """
    Run the full inference cascade on a batch of network flows.
    Returns a list of policy decisions.
    """
    try:
        if not request.flows:
            return []
            
        df = pd.DataFrame(request.flows)
        decisions = predict(df)
        return [d.to_dict() for d in decisions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction error: {str(e)}")
