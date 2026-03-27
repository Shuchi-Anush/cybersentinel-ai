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

from src.core.paths import DATA_DIR as BASE_DATA_DIR, MODELS_DIR

DATA_DIR = BASE_DATA_DIR / "raw" / "CICIDS2017"
MODEL_DIR = MODELS_DIR
OUTPUT_DIR = MODELS_DIR.parent / "outputs"

MODEL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------
# SCENARIO BASED DATA SPLIT (Prevents data leakage)
# ---------------------------------------------------------

TRAIN_FILES = [
    "Monday-WorkingHours.pcap_ISCX.csv",
    "Tuesday-WorkingHours.pcap_ISCX.csv",
    "Wednesday-workingHours.pcap_ISCX.csv",
]

TEST_FILES = [
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
]


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


def train_models():

    print("\nLoading CIC-IDS2017 dataset...\n")

    train_df = load_cic_dataset(TRAIN_FILES)
    test_df = load_cic_dataset(TEST_FILES)

    train_df = clean_dataset(train_df)
    test_df = clean_dataset(test_df)

    X_train, y_train = prepare_features(train_df)
    X_test, y_test = prepare_features(test_df)

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
