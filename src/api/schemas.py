"""
CyberSentinel AI — API Schemas
Author: CyberSentinel ML-LAB

Defines Pydantic models for the FastAPI request/response payloads.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FlowRequest(BaseModel):
    """Single network flow prediction request."""
    features: Dict[str, float] = Field(
        ..., 
        description="Dictionary of network flow features. Keys should match selected feature names.",
        example={"Flow Duration": 120.5, "Total Fwd Packets": 2.0}
    )


class FlowBatchRequest(BaseModel):
    """Batch network flow prediction request."""
    flows: List[Dict[str, float]] = Field(
        ..., 
        description="List of dictionaries representing network flows."
    )


class PredictResponse(BaseModel):
    """Structured policy decision response."""
    action: str = Field(..., description="ALLOW, QUARANTINE, or DENY")
    binary_pred: int = Field(..., description="0 for Benign, 1 for Attack")
    confidence: float = Field(..., description="Confidence score of the binary prediction")
    attack_type: Optional[str] = Field(None, description="Type of attack if binary_pred is 1")
    timestamp: str = Field(..., description="Timestamp of the decision")
    reason: str = Field(..., description="Human-readable reason for the action")
