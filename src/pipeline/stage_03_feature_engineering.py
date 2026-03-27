from src.features.feature_engineering import generate_features


def run_feature_engineering(X_train, X_test):

    print("Stage 3: Feature Engineering")

    x_train_feat = generate_features(X_train)
    x_test_feat = generate_features(X_test)

    return x_train_feat, x_test_feat
