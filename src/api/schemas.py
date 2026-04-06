"""
CyberSentinel AI — API Schemas
Author: CyberSentinel ML-LAB

Defines Pydantic models for the FastAPI request/response payloads.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    """Single network flow prediction request."""

    features: dict

    @field_validator("features")
    @classmethod
    def validate_features(cls, v):
        if not v:
            raise ValueError("features cannot be empty")
        return v


class FlowRequest(PredictRequest):
    """Legacy alias for PredictRequest."""
    pass


class FlowBatchRequest(BaseModel):
    """Batch network flow prediction request."""

    flows: List[Dict[str, float]] = Field(
        ..., description="List of dictionaries representing network flows."
    )


class PredictResponse(BaseModel):
    """Strict policy decision response (Contract enforced)."""

    action: str = Field(..., description="ALLOW, QUARANTINE, or DENY")
    confidence: float = Field(
        ..., description="Confidence score of the binary prediction"
    )
    attack_type: Optional[str] = Field(
        None, description="Type of attack if binary_pred is 1"
    )
