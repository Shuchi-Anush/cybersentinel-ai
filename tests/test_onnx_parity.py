import joblib
import numpy as np
import pytest
import pandas as pd
from pathlib import Path

from src.core.paths import MODELS_DIR

import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Skipping model-dependent tests in CI"
)

# Pytest fixture to load models
@pytest.fixture(scope="module")
def artifacts():
    import onnxruntime as rt
    
    # Load Python Base Model
    sk_base = joblib.load(MODELS_DIR / "binary" / "base_binary_model.pkl")
    
    # Load ONNX Base Model
    onnx_base = rt.InferenceSession(str(MODELS_DIR / "binary" / "base_binary_model.onnx"))
    
    return sk_base, onnx_base

def test_onnx_sklearn_parity(artifacts):
    sk_base, onnx_base = artifacts
    
    # Generate random scaled float32 inputs matching the 40 feature geometry
    x_test = np.random.rand(100, 40).astype(np.float32)
    
    # Sklearn Execution
    sk_preds = sk_base.predict(x_test)
    sk_probas = sk_base.predict_proba(x_test)
    
    # ONNX Execution
    input_b = onnx_base.get_inputs()[0].name
    onnx_outs = onnx_base.run(None, {input_b: x_test})
    
    onnx_preds = onnx_outs[0]
    
    # Assert exact label match
    np.testing.assert_array_equal(sk_preds, onnx_preds, "ONNX and Sklearn binary labels do not match!")
    
    # Assert probability geometry (probas is element 1, a list of dicts)
    onnx_probas_list = onnx_outs[1]
    
    onnx_probas_parsed = np.array([
         [row[0], row[1]] for row in onnx_probas_list
    ])
    
    np.testing.assert_allclose(sk_probas, onnx_probas_parsed, rtol=1e-5, err_msg="ONNX Probabilities diverged from Sklearn Base RF!")

