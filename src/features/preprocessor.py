"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Preprocessing Module (Stage 2)
Author: CyberSentinel ML-LAB

Responsibilities:
    1. Load merged_cleaned.csv from data/processed/
    2. Apply selected features list from Stage 1 (selected_features.json)
    3. Stratified train/val/test split (70 / 15 / 15)
    4. Fit StandardScaler on train split only — transform val & test
    5. Save scaler.pkl to models/
    6. Save processed splits to data/processed/ as parquet

Outputs:
    data/processed/
        X_train.parquet, y_train_binary.parquet, y_train_label.parquet
        X_val.parquet,   y_val_binary.parquet,   y_val_label.parquet
        X_test.parquet,  y_test_binary.parquet,  y_test_label.parquet
    models/
        scaler.pkl
        preprocessing_metadata.json
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.features.selector import load_selected_features

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("preprocessor")


# ------------------------------------------------------------------
# Path configuration
# ------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
CONFIG_PATH = PROJECT_ROOT / "configs" / "training.yaml"

SCALER_PATH = MODELS_DIR / "scaler.pkl"
METADATA_PATH = MODELS_DIR / "preprocessing_metadata.json"
FEATURES_JSON = PROCESSED_DIR / "selected_features.json"


# ------------------------------------------------------------------
# Config loader
# ------------------------------------------------------------------

def _load_config() -> dict:
    """Load training section from training.yaml."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("training", {})
    return {}


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise column names: accept 'Label'/'Binary' and rename to lowercase.
    Raises ValueError if neither 'label' nor 'binary' can be found.
    """
    rename_map = {}
    for col in ("label", "binary"):
        if col not in df.columns:
            title_col = col.title()
            if title_col in df.columns:
                rename_map[title_col] = col
    if rename_map:
        df = df.rename(columns=rename_map)
    missing = [c for c in ("label", "binary") if c not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset missing required columns: {missing}. "
            f"Available columns: {df.columns.tolist()[:20]}…"
        )
    return df


def _sanitise(x: pd.DataFrame) -> pd.DataFrame:
    """Replace Inf/NaN; cast to float32 to halve memory footprint."""
    x = x.replace([np.inf, -np.inf], np.nan)
    x = x.fillna(x.median(numeric_only=True))
    return x.astype(np.float32)


def _save_split(
    x: pd.DataFrame,
    y_binary: pd.Series,
    y_label: pd.Series,
    name: str,
    out_dir: Path,
) -> None:
    """Persist one split (train / val / test) as parquet files."""
    x.to_parquet(out_dir / f"X_{name}.parquet", index=False)
    y_binary.to_frame().to_parquet(out_dir / f"y_{name}_binary.parquet", index=False)
    y_label.to_frame().to_parquet(out_dir / f"y_{name}_label.parquet", index=False)
    logger.info(
        "Saved %s split → X=%s  binary=%s  label=%s",
        name, x.shape, y_binary.shape, y_label.shape,
    )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def run_preprocessing(
    data_path: Optional[Path] = None,
    features_path: Optional[Path] = None,
    out_dir: Optional[Path] = None,
    scaler_path: Optional[Path] = None,
    test_size: Optional[float] = None,
    val_size: Optional[float] = None,
    random_state: Optional[int] = None,
) -> dict[str, pd.DataFrame]:
    """
    Full preprocessing pipeline (Stage 2).

    Loads the cleaned merged dataset, restricts it to the features
    selected in Stage 1, performs a stratified 70/15/15 split, fits a
    StandardScaler on the training portion only, and persists all
    artifacts to disk.

    Parameters
    ----------
    data_path : Path, optional
        Path to merged_cleaned.csv.  Defaults to data/processed/merged_cleaned.csv.
    features_path : Path, optional
        Path to selected_features.json from Stage 1.  Defaults to
        data/processed/selected_features.json.
    out_dir : Path, optional
        Directory for parquet split files.  Defaults to data/processed/.
    scaler_path : Path, optional
        Where to save scaler.pkl.  Defaults to models/scaler.pkl.
    test_size : float, optional
        Fraction for test split (default 0.15 from config).
    val_size : float, optional
        Fraction *of the train+val pool* for validation (default 0.15).
    random_state : int, optional
        Seed (default 42 from config).

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys: X_train, X_val, X_test, y_train_binary, y_val_binary,
              y_test_binary, y_train_label, y_val_label, y_test_label.
    """
    t0 = time.time()

    # ---- resolve parameters -----------------------------------------
    cfg = _load_config()
    data_path = data_path or (PROCESSED_DIR / "merged_cleaned.csv")
    features_path = features_path or FEATURES_JSON
    out_dir = out_dir or PROCESSED_DIR
    scaler_path = scaler_path or SCALER_PATH
    test_size = test_size if test_size is not None else cfg.get("test_size", 0.15)
    val_size = val_size if val_size is not None else cfg.get("val_size", 0.15)
    random_state = random_state if random_state is not None else cfg.get("random_state", 42)

    out_dir.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # ---- load dataset -----------------------------------------------
    logger.info("Loading dataset from: %s", data_path)
    df = pd.read_csv(data_path, low_memory=False)
    logger.info("Dataset shape: %s", df.shape)
    df = _validate_columns(df)

    # ---- load selected features from Stage 1 -------------------------
    logger.info("Loading selected features from: %s", features_path)
    selected_features = load_selected_features(features_path)
    logger.info("Using %d selected features", len(selected_features))

    # Guard: ensure all selected features exist in the loaded dataframe
    missing_cols = [f for f in selected_features if f not in df.columns]
    if missing_cols:
        raise ValueError(
            f"{len(missing_cols)} selected features not found in dataset.\n"
            f"First 10 missing: {missing_cols[:10]}"
        )

    # ---- build feature matrix & label series --------------------------
    x = df[selected_features].copy()
    y_binary = df["binary"].astype(np.int8)
    y_label = df["label"].astype(str)

    x = _sanitise(x)

    logger.info(
        "Class distribution (binary):\n%s",
        y_binary.value_counts().to_string(),
    )

    # ---- stratified split: full → trainval / test --------------------
    # Stratify on binary label
    x_trainval, x_test, y_binary_trainval, y_binary_test, y_label_trainval, y_label_test = \
        train_test_split(
            x, y_binary, y_label,
            test_size=test_size,
            stratify=y_binary,
            random_state=random_state,
        )

    # Proportional val size from trainval pool
    # e.g. 0.15 test, 0.15 val → val fraction of trainval = 0.15/(1-0.15) ≈ 0.176
    val_fraction = val_size / (1.0 - test_size)
    x_train, x_val, y_binary_train, y_binary_val, y_label_train, y_label_val = \
        train_test_split(
            x_trainval, y_binary_trainval, y_label_trainval,
            test_size=val_fraction,
            stratify=y_binary_trainval,
            random_state=random_state,
        )

    logger.info(
        "Split sizes — train: %d  val: %d  test: %d",
        len(x_train), len(x_val), len(x_test),
    )

    # ---- fit scaler on train only -----------------------------------
    logger.info("Fitting StandardScaler on training split…")
    scaler = StandardScaler()
    x_train_scaled = pd.DataFrame(
        scaler.fit_transform(x_train),
        columns=selected_features,
        dtype=np.float32,
    )
    x_val_scaled = pd.DataFrame(
        scaler.transform(x_val),
        columns=selected_features,
        dtype=np.float32,
    )
    x_test_scaled = pd.DataFrame(
        scaler.transform(x_test),
        columns=selected_features,
        dtype=np.float32,
    )

    # ---- save scaler ------------------------------------------------
    joblib.dump(scaler, scaler_path)
    logger.info("Saved scaler → %s", scaler_path)

    # ---- save splits ------------------------------------------------
    # Reset index so parquet row numbers are clean
    for frame in (
        x_train_scaled, x_val_scaled, x_test_scaled,
        y_binary_train, y_binary_val, y_binary_test,
        y_label_train, y_label_val, y_label_test,
    ):
        frame.reset_index(drop=True, inplace=True)

    _save_split(x_train_scaled, y_binary_train, y_label_train, "train", out_dir)
    _save_split(x_val_scaled, y_binary_val, y_label_val, "val", out_dir)
    _save_split(x_test_scaled, y_binary_test, y_label_test, "test", out_dir)

    elapsed = time.time() - t0

    # ---- save metadata ----------------------------------------------
    metadata = {
        "source_dataset": str(data_path.name),
        "selected_features": selected_features,
        "feature_count": len(selected_features),
        "split": {
            "train_rows": int(len(x_train_scaled)),
            "val_rows": int(len(x_val_scaled)),
            "test_rows": int(len(x_test_scaled)),
            "test_size": test_size,
            "val_size": val_size,
            "random_state": random_state,
        },
        "scaler": {
            "type": "StandardScaler",
            "path": str(scaler_path),
            "fitted_on": "train_split_only",
        },
        "class_distribution": {
            "train": y_binary_train.value_counts().to_dict(),
            "val": y_binary_val.value_counts().to_dict(),
            "test": y_binary_test.value_counts().to_dict(),
        },
        "elapsed_seconds": round(elapsed, 2),
    }
    # Convert int8/int keys to plain int for JSON serialisation
    def _jsonify(obj):
        if isinstance(obj, dict):
            return {int(k) if isinstance(k, (np.integer,)) else k: _jsonify(v)
                    for k, v in obj.items()}
        return obj

    with open(METADATA_PATH, "w") as fh:
        json.dump(_jsonify(metadata), fh, indent=2)
    logger.info("Saved preprocessing metadata → %s", METADATA_PATH)

    logger.info("Preprocessing complete in %.1fs", elapsed)

    return {
        "X_train": x_train_scaled,
        "X_val": x_val_scaled,
        "X_test": x_test_scaled,
        "y_train_binary": y_binary_train,
        "y_val_binary": y_binary_val,
        "y_test_binary": y_binary_test,
        "y_train_label": y_label_train,
        "y_val_label": y_label_val,
        "y_test_label": y_label_test,
    }


# ------------------------------------------------------------------
# Loader utilities (used at training / inference time)
# ------------------------------------------------------------------

def load_splits(
    split: str = "train",
    out_dir: Optional[Path] = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Load a previously saved split from parquet files.

    Parameters
    ----------
    split : str
        One of 'train', 'val', or 'test'.
    out_dir : Path, optional
        Directory containing the parquet files.

    Returns
    -------
    tuple[pd.DataFrame, pd.Series, pd.Series]
        X, y_binary, y_label for the requested split.
    """
    if split not in ("train", "val", "test"):
        raise ValueError(f"split must be 'train', 'val', or 'test'; got '{split}'")
    out_dir = out_dir or PROCESSED_DIR
    x = pd.read_parquet(out_dir / f"X_{split}.parquet")
    y_binary = pd.read_parquet(out_dir / f"y_{split}_binary.parquet").squeeze()
    y_label = pd.read_parquet(out_dir / f"y_{split}_label.parquet").squeeze()
    logger.info("Loaded %s split — X=%s", split, x.shape)
    return x, y_binary, y_label


def load_scaler(path: Optional[Path] = None) -> StandardScaler:
    """
    Load the fitted StandardScaler from disk.

    Parameters
    ----------
    path : Path, optional
        Override default scaler path (models/scaler.pkl).

    Returns
    -------
    StandardScaler
    """
    path = path or SCALER_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Scaler not found at '{path}'. "
            "Run `run_preprocessing()` first."
        )
    scaler = joblib.load(path)
    logger.info("Loaded scaler from: %s", path)
    return scaler


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="CyberSentinel-AI — Preprocessing (Stage 2)"
    )
    parser.add_argument("--data", type=Path, default=None,
                        help="Path to merged_cleaned.csv")
    parser.add_argument("--features", type=Path, default=None,
                        help="Path to selected_features.json from Stage 1")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output directory for parquet splits")
    parser.add_argument("--test-size", type=float, default=None)
    parser.add_argument("--val-size", type=float, default=None)
    parser.add_argument("--random-state", type=int, default=None)
    args = parser.parse_args()

    splits = run_preprocessing(
        data_path=args.data,
        features_path=args.features,
        out_dir=args.out_dir,
        test_size=args.test_size,
        val_size=args.val_size,
        random_state=args.random_state,
    )

    print("\nPreprocessing complete. Split shapes:")
    for key, frame in splits.items():
        print(f"  {key:20s} → {frame.shape}")
