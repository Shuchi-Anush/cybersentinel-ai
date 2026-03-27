"""
CyberSentinel AI — Pipeline Stage 02: Preprocessing
Delegates to src.features.preprocessor (Stage 2 implementation).
"""

from src.features.preprocessor import run_preprocessing


def run_stage_02_preprocessing() -> dict:
    """
    Execute Stage 2 preprocessing.

    Loads merged_cleaned.csv, applies selected features, performs
    stratified splits, fits + saves StandardScaler, and persists
    all parquet splits to DATA_DIR / "processed".

    Returns
    -------
    dict
        Keys: X_train, X_val, X_test, y_train_binary, y_val_binary,
              y_test_binary, y_train_label, y_val_label, y_test_label
    """
    print("\n--- Stage 2: Preprocessing ---")
    splits = run_preprocessing()
    print(f"  Train rows  : {len(splits['X_train']):,}")
    print(f"  Val rows    : {len(splits['X_val']):,}")
    print(f"  Test rows   : {len(splits['X_test']):,}")
    print(f"  Features    : {splits['X_train'].shape[1]}")
    return splits
