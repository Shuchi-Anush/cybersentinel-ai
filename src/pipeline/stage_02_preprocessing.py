from src.data.preprocess import clean_dataset

def run_preprocessing(X_train, X_test):

    print("Stage 2: Data Preprocessing")

    X_train_clean = clean_dataset(X_train)
    X_test_clean = clean_dataset(X_test)

    return X_train_clean, X_test_clean