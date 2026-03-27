from src.data.load_data import load_cic_dataset


def run_data_ingestion():
    print("Stage 1: Data Ingestion")

    X_train, X_test, y_train, y_test = load_cic_dataset()

    return X_train, X_test, y_train, y_test
