"""
CyberSentinel AI — API Services
Author: CyberSentinel ML-LAB

Centralized logic builders for API responses.
"""

def build_response(action, confidence, attack_type=None, prediction=None, probability=None, trust=None):
    """
    Enforces the exactly required API response schema with Zero-Trust extensions.
    """
    try:
        confidence = float(confidence) if confidence is not None else 0.0
    except Exception:
        confidence = 0.0

    return {
        "action": str(action) if action is not None else "UNKNOWN",
        "confidence": round(confidence, 6),
        "attack_type": str(attack_type) if attack_type is not None else None,
        "prediction": str(prediction) if prediction is not None else None,
        "probability": round(float(probability), 6) if probability is not None else None,
        "trust": trust
    }
