import pytest
import pandas as pd
from src.inference.inference_pipeline import InferencePipeline
from src.features.preprocessor import load_splits
import os

if not os.path.exists("models"):
    pytest.skip("Skipping pipeline test: models not available", allow_module_level=True)

def test_pipeline_instantiation():
    """Verify that all production artifacts are loaded correctly."""
    try:
        pipeline = InferencePipeline()
        assert pipeline is not None
        assert hasattr(pipeline, "_features")
        assert len(pipeline._features) > 0
    except Exception as e:
        pytest.fail(f"InferencePipeline failed to load artifacts: {e}")

def test_pipeline_inference_smoke():
    """Run a single-batch inference on sample data from the test split."""
    pipeline = InferencePipeline()
    
    # Load sample rows from the test split
    # Note: test split should exist if pipeline stages 1-2 were run previously
    try:
        x_test, _, _ = load_splits("test")
    except FileNotFoundError:
        pytest.skip("Processed test split not found. Skipping smoke test.")
        
    sample_df = x_test.head(5)
    decisions = pipeline.predict(sample_df)
    
    assert len(decisions) == 5
    for d in decisions:
        assert d.action is not None
        assert 0.0 <= d.confidence <= 1.0
        # attack_type is None for benign traffic, which is valid
        if d.action.value != "ALLOW":
            assert isinstance(d.attack_type, str)
