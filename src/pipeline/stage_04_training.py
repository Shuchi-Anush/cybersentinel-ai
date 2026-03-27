"""
CyberSentinel AI — Pipeline Stage 04: Binary + Multi-class Training
Orchestrates Stage 3 (binary) then Stage 4 (multi-class) in sequence.
Binary model must exist before multi-class can filter attack rows.
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from src.training.binary_trainer import train_binary_classifier
from src.training.multiclass_trainer import train_multiclass_classifier


def run_stage_04_training() -> dict:
    """
    Execute binary and multi-class training in sequence.

    Step 1 — Binary classifier (Benign vs Attack)
        Loads scaled train/val splits from Stage 2.
        Saves model to MODELS_DIR / "binary".

    Step 2 — Multi-class classifier (Attack type)
        Loads same splits; filters to attack rows only (binary==1).
        Saves model + encoder to MODELS_DIR / "multiclass".

    Returns
    -------
    dict with keys:
        'binary_model'     : RandomForestClassifier
        'multiclass_model' : RandomForestClassifier
        'label_encoder'    : LabelEncoder
    """
    print("\n--- Stage 3: Binary Classifier Training ---")
    binary_model: RandomForestClassifier = train_binary_classifier()

    print("\n--- Stage 4: Multi-class Classifier Training ---")
    multiclass_model: RandomForestClassifier
    encoder: LabelEncoder
    multiclass_model, encoder = train_multiclass_classifier()

    return {
        "binary_model": binary_model,
        "multiclass_model": multiclass_model,
        "label_encoder": encoder,
    }
