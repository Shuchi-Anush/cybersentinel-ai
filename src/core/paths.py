from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

MODELS_DIR = ROOT_DIR / "models"
CONFIGS_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
EVAL_DIR = ARTIFACTS_DIR / "evaluation"
TESTING_ARTIFACTS_DIR = ARTIFACTS_DIR / "testing"

