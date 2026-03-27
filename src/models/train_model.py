"""
CyberSentinel AI
Model Training with MLflow Tracking
"""

import mlflow
import mlflow.sklearn
import pandas as pd

from src.core.paths import DATA_DIR
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score


def train():

    # -----------------------------
    # MLflow setup
    # -----------------------------
    mlflow.set_experiment("cybersentinel_intrusion_detection")

    with mlflow.start_run():
        # -----------------------------
        # Load processed dataset
        # -----------------------------
        df = pd.read_csv(DATA_DIR / "processed" / "processed_data.csv")

        X = df.drop("Label", axis=1)
        y = df["Label"]

        # -----------------------------
        # Train-test split
        # -----------------------------
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # -----------------------------
        # Pipeline steps
        # -----------------------------
        scaler = StandardScaler()
        selector = SelectKBest(score_func=f_classif, k=20)
        pca = PCA(n_components=0.95)
        model = DecisionTreeClassifier(random_state=42)

        # -----------------------------
        # Fit pipeline
        # -----------------------------
        X_train = scaler.fit_transform(X_train)
        X_train = selector.fit_transform(X_train, y_train)
        X_train = pca.fit_transform(X_train)

        model.fit(X_train, y_train)

        # -----------------------------
        # Test pipeline
        # -----------------------------
        X_test = scaler.transform(X_test)
        X_test = selector.transform(X_test)
        X_test = pca.transform(X_test)

        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)

        print("Accuracy:", accuracy)

        # -----------------------------
        # MLflow logging
        # -----------------------------
        mlflow.log_param("model", "DecisionTree")
        mlflow.log_param("features_selected", 20)
        mlflow.log_param("pca_variance", 0.95)

        mlflow.log_metric("accuracy", accuracy)

        mlflow.sklearn.log_model(model, "intrusion_detection_model")

        print("Model logged to MLflow")


if __name__ == "__main__":
    train()
