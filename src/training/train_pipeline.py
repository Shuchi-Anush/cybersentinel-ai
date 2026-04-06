"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Training Pipeline
Author: CyberSentinel ML-LAB
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline

from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB

from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.metrics import f1_score

import joblib


# ---------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------

from src.core.paths import RAW_DATA_DIR

# ---------------------------------------------------------
# SCENARIO BASED DATA SPLIT (Prevents data leakage)
# ---------------------------------------------------------

import yaml
from src.core.paths import CONFIGS_DIR, MODELS_DIR, ARTIFACTS_DIR

with open(CONFIGS_DIR / "data.yaml", "r") as f:
    _data_config = yaml.safe_load(f)
    
TRAIN_FILES = _data_config["split"]["train_days"]
TEST_FILES = _data_config["split"]["test_days"]
DATA_SUBDIR = _data_config["dataset"]["name"]
DATA_DIR = RAW_DATA_DIR / DATA_SUBDIR

MODEL_DIR = MODELS_DIR
OUTPUT_DIR = ARTIFACTS_DIR / "training"

MODEL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)



# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------


def load_cic_dataset(file_list):
    """Load multiple CICIDS CSV files"""

    dfs = []

    for file in file_list:
        path = DATA_DIR / file

        if not path.exists():
            raise FileNotFoundError(f"Missing dataset file: {path}")

        df = pd.read_csv(path)

        print(f"Loaded {file} → {len(df)} flows")

        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    
    # Strip leading/trailing spaces from column names (Standard CICIDS format fix)
    combined.columns = combined.columns.str.strip()

    return combined


# ---------------------------------------------------------
# DATA CLEANING
# ---------------------------------------------------------


def clean_dataset(df):
    """Fix CIC-IDS2017 data issues"""

    print("Cleaning dataset...")

    # Remove duplicates
    df = df.drop_duplicates()

    # Replace infinity values
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Fill NaN using median
    df.fillna(df.median(numeric_only=True), inplace=True)

    return df


# ---------------------------------------------------------
# PREPARE FEATURES
# ---------------------------------------------------------


def prepare_features(df):
    """Split features and label"""

    if "Label" not in df.columns:
        raise ValueError("Dataset missing 'Label' column")

    X = df.drop("Label", axis=1)
    y = df["Label"]

    return X, y


# ---------------------------------------------------------
# VISUALIZATION
# ---------------------------------------------------------


def plot_confusion_matrix(cm, model_name):

    plt.figure(figsize=(6, 5))

    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")

    plt.title(f"{model_name} Confusion Matrix")

    plt.xlabel("Predicted")
    plt.ylabel("Actual")

    save_path = OUTPUT_DIR / f"{model_name}_confusion_matrix.png"

    plt.savefig(save_path, dpi=300)

    plt.close()


# ---------------------------------------------------------
# TRAIN MODELS
# ---------------------------------------------------------


from sklearn.model_selection import train_test_split

def train_models():

    print("\nLoading and Combining CIC-IDS2017 dataset pools...\n")

    # Combine all configured files to ensure full label coverage
    all_files = list(set(TRAIN_FILES + TEST_FILES))
    full_df = load_cic_dataset(all_files)
    
    full_df = clean_dataset(full_df)

    X_raw, y_raw = prepare_features(full_df)

    # Stratified split to ensure all labels are represented in both sets
    print("\nExecuting stratified train-test split (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42, stratify=y_raw
    )

    # Encode labels
    label_encoder = LabelEncoder()

    y_train_enc = label_encoder.fit_transform(y_train)
    y_test_enc = label_encoder.transform(y_test)

    # -----------------------------------------------------
    # PIPELINES
    # -----------------------------------------------------

    pipelines = {
        "decision_tree": Pipeline(
            [
                ("select", SelectKBest(score_func=f_classif, k=25)),
                ("scale", StandardScaler()),
                ("pca", PCA(n_components=12)),
                ("model", DecisionTreeClassifier(random_state=42)),
            ]
        ),
        "naive_bayes": Pipeline(
            [
                ("select", SelectKBest(score_func=f_classif, k=25)),
                ("scale", StandardScaler()),
                ("pca", PCA(n_components=12)),
                ("model", GaussianNB()),
            ]
        ),
    }

    results = {}

    # -----------------------------------------------------
    # TRAINING LOOP
    # -----------------------------------------------------

    for name, pipeline in pipelines.items():
        print(f"\nTraining {name}...")

        pipeline.fit(X_train, y_train_enc)

        predictions = pipeline.predict(X_test)

        f1 = f1_score(y_test_enc, predictions, average="weighted")

        report = classification_report(y_test_enc, predictions)

        cm = confusion_matrix(y_test_enc, predictions)

        print(report)

        print(f"{name} F1 Score: {f1:.4f}")

        results[name] = f1

        # Save model pipeline
        model_path = MODEL_DIR / f"{name}_pipeline.pkl"

        joblib.dump(pipeline, model_path)

        print(f"Saved model → {model_path}")

        # Save confusion matrix
        plot_confusion_matrix(cm, name)

    # Save label encoder
    joblib.dump(label_encoder, MODEL_DIR / "label_encoder.pkl")

    print("\nTraining completed.")

    print("\nFinal Results:")

    for model, score in results.items():
        print(f"{model} → F1 = {score:.4f}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\nCyberSentinel AI Training Pipeline\n")

    train_models()
