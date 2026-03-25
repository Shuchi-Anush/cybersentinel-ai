"""
CyberSentinel AI — src/data/preprocess.py

Legacy shim kept for backward compatibility with train_pipeline.py.
New code should use:  from src.features.preprocessor import run_preprocessing
"""
import numpy as np
import pandas as pd


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Basic data cleaning used by the legacy train_pipeline.py.

    Removes duplicates, replaces Inf values, and fills NaN with column median.
    For the new modular preprocessing pipeline see src/features/preprocessor.py.
    """
    df = df.drop_duplicates()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(df.median(numeric_only=True))
    return df
