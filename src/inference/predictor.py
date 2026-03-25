"""
CyberSentinel AI — src/inference/predictor.py

Legacy shim / schema documentation.
New code should use:  from src.inference.inference_pipeline import InferencePipeline

Input Schema
------------
The inference pipeline expects a DataFrame (or dict) whose columns
include *at minimum* the features listed in data/processed/selected_features.json.

Extra columns are silently dropped.
Missing selected features are filled with 0.0 and logged as a warning.

Numeric types only — any string columns are not supported.
Inf and NaN values are replaced with 0.0 before scaling.
"""
from src.inference.inference_pipeline import InferencePipeline, predict, predict_one

__all__ = ["InferencePipeline", "predict", "predict_one"]
