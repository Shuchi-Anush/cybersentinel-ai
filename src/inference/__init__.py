"""
CyberSentinel AI — inference package

Public API
----------
    from src.inference import InferencePipeline
    from src.inference import predict, predict_one
"""
from src.inference.inference_pipeline import (
    InferencePipeline,
    predict,
    predict_one,
)

__all__ = [
    "InferencePipeline",
    "predict",
    "predict_one",
]
