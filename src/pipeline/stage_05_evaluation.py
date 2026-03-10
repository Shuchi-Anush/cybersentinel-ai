from src.models.evaluate import evaluate_model

def run_evaluation(model, X_test, y_test):

    print("Stage 5: Evaluation")

    metrics = evaluate_model(model, X_test, y_test)

    return metrics