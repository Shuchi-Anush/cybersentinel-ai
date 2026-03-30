import joblib
from pathlib import Path
import random

def get_base_features():
    """Load the official production feature list."""
    f_path = Path("models/binary/features.pkl")
    if not f_path.exists():
        return []
    return joblib.load(f_path)

class PayloadFactory:
    def __init__(self, features=None):
        self.features = features or get_base_features()
    
    def generate_single(self, corrupt=False):
        """Generate a single predict payload."""
        if corrupt:
            # Corrupt payload with missing critical features or wrong types
            return {"features": {"invalid_col": 1.0}}
            
        return {
            "features": {f: random.uniform(0, 100) for f in self.features}
        }
        
    def generate_batch(self, count=10):
        """Generate a batch predict payload."""
        return {
            "flows": [
                {f: random.uniform(0, 100) for f in self.features}
                for _ in range(count)
            ]
        }
