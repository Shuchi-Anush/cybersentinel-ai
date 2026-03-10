from src.training.train_pipeline import train_models

def run_training(X_train, y_train):

    print("Stage 4: Model Training")

    model = train_models(X_train, y_train)

    return model