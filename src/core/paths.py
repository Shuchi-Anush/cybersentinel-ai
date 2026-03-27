from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

MODELS_DIR = ROOT_DIR / "models"
CONFIGS_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
EVAL_DIR = MODELS_DIR / "eval"
