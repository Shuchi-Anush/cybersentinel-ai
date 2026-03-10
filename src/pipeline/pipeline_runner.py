from src.pipeline.stage_01_data_ingestion import run_data_ingestion
from src.pipeline.stage_02_preprocessing import run_preprocessing
from src.pipeline.stage_03_feature_engineering import run_feature_engineering
from src.pipeline.stage_04_training import run_training
from src.pipeline.stage_05_evaluation import run_evaluation


def run_pipeline():

    X_train, X_test, y_train, y_test = run_data_ingestion()

    X_train, X_test = run_preprocessing(X_train, X_test)

    X_train, X_test = run_feature_engineering(X_train, X_test)

    model = run_training(X_train, y_train)

    metrics = run_evaluation(model, X_test, y_test)

    print("Pipeline completed")
    print(metrics)


if __name__ == "__main__":
    run_pipeline()