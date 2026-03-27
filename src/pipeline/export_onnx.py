import argparse
import logging
from pathlib import Path

import joblib
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

from src.core.paths import MODELS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("onnx_exporter")

def export_model(pkl_path: Path, onnx_path: Path, n_features: int):
    logger.info(f"Loading model from {pkl_path}...")
    try:
        model = joblib.load(pkl_path)
    except Exception as e:
        logger.error(f"Failed to load {pkl_path}: {e}")
        return

    logger.info(f"Converting model to ONNX with n_features={n_features}...")
    initial_type = [('float_input', FloatTensorType([None, n_features]))]
    
    try:
        onnx_model = convert_sklearn(model, initial_types=initial_type)
        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())
        logger.info(f"Successfully exported ONNX to {onnx_path}")
    except Exception as e:
        logger.error(f"Failed to convert or save ONNX: {e}")

def main():
    # Load feature count dynamically to ensure parity
    features_path = MODELS_DIR / "binary" / "features.pkl"
    try:
        features = joblib.load(features_path)
        n_features = len(features)
        logger.info(f"Loaded {n_features} features from metadata.")
    except Exception as e:
        logger.info("Falling back to default 40 features.")
        n_features = 40
        
    binary_pkl = MODELS_DIR / "binary" / "base_binary_model.pkl"
    binary_onnx = MODELS_DIR / "binary" / "base_binary_model.onnx"
    export_model(binary_pkl, binary_onnx, n_features)
    
    multi_pkl = MODELS_DIR / "multiclass" / "model.pkl"
    multi_onnx = MODELS_DIR / "multiclass" / "multiclass_model.onnx"
    export_model(multi_pkl, multi_onnx, n_features)

if __name__ == "__main__":
    main()
