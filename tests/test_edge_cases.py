import os
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from src.inference.inference_pipeline import InferencePipeline

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Skipping model-dependent tests in CI",
)

if not os.path.exists("models"):
    pytest.skip("Skipping edge case test: models not available", allow_module_level=True)


def test_edge_cases():
    print("Initializing Pipeline...")
    pipe = InferencePipeline()
    pipe.load()

    print("\n--- TEST 1: Missing Features ---")
    df_missing = pd.DataFrame({"Destination Port": [80], "Flow Duration": [100]})
    try:
        pipe.predict(df_missing)
        print("❌ FAIL: Did not catch missing features!")
    except HTTPException as e:
        assert e.status_code == 422
        print(f"✅ PASS: Missing features blocked. HTTP {e.status_code} - {e.detail}")

    print("\n--- TEST 2: NaN / Inf vectors ---")
    df_nan = pd.DataFrame([np.random.rand(40)], columns=pipe._features)
    df_nan.iloc[0, 5] = np.nan
    try:
        pipe.predict(df_nan)
        print("❌ FAIL: Did not catch NaN features!")
    except HTTPException as e:
        assert e.status_code == 422
        print(f"✅ PASS: NaN bounds blocked. HTTP {e.status_code} - {e.detail}")

    print("\n--- TEST 3: Incorrect feature order ---")
    df_correct = pd.DataFrame([np.random.rand(40)], columns=pipe._features)
    shuffled_cols = list(pipe._features)
    shuffled_cols.reverse()
    df_shuffled = df_correct[shuffled_cols]

    res1 = pipe.predict(df_correct)
    res2 = pipe.predict(df_shuffled)

    assert res1[0]["action"] == res2[0]["action"], "❌ FAIL: Output mismatch."
    print("✅ PASS: Feature mapping successfully aligned native matrix order dynamically before inference.")

    print("\n--- TEST 4: ONNX Malformed Protection ---")
    original_run = pipe._binary_sess.run
    pipe._binary_sess.run = lambda a, b: [np.array([1])]  # Returns 1 tensor instead of 2

    df_valid = pd.DataFrame([np.random.rand(40)], columns=pipe._features)
    try:
        pipe.predict(df_valid)
        print("❌ FAIL: Did not catch ONNX output length corruption!")
    except RuntimeError as e:
        print(f"✅ PASS: Caught internal ONNX crash. Msg: {e}")

    pipe._binary_sess.run = original_run


if __name__ == "__main__":
    test_edge_cases()
