import os
import pytest
import pandas as pd
from src.inference.inference_pipeline import InferencePipeline

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Skipping model-dependent tests in CI",
)

if not os.path.exists("models"):
    pytest.skip("Skipping pipeline test: models not available", allow_module_level=True)


def test_pipeline_instantiation():
    """Verify instantiation is side-effect free, then load() works."""
    pipeline = InferencePipeline()
    assert pipeline is not None
    assert not pipeline._loaded

    pipeline.load()
    assert pipeline._loaded
    assert len(pipeline._features) > 0


def test_pipeline_inference_smoke():
    """Run a single-batch inference on fabricated data."""
    pipeline = InferencePipeline()
    pipeline.load()

    sample_df = pd.DataFrame(
        [dict(zip(pipeline._features, [0.0] * len(pipeline._features)))]
    )
    decisions = pipeline.predict(sample_df)

    assert len(decisions) == 1
    d = decisions[0]
    assert "action" in d
    assert "confidence" in d
    assert 0.0 <= float(d["confidence"]) <= 1.0
