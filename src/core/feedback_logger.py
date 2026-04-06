"""
CyberSentinel AI — Anomaly Feedback Logger
Author: CyberSentinel ML-LAB

Asynchronous logging architecture for production monitoring.
"""

import os
import json
import logging
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("feedback_logger")

# Singleton executor to prevent thread spawning per request
executor = ThreadPoolExecutor(max_workers=2)

# Ensure artifacts directory exists at startup
os.makedirs("artifacts", exist_ok=True)
FILE_PATH = "artifacts/feedback_log.jsonl"

def log_feedback_async(event: dict):
    """
    Non-blocking, sampling-based logging (20% sample rate).
    """
    # 20% Sampling Logic
    if random.random() > 0.2:
        return
        
    def _safe_log(data: dict):
        try:
            # Metadata enrichment
            data["timestamp"] = datetime.utcnow().isoformat()
            
            with open(FILE_PATH, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log feedback: {e}")

    # Submit task to pooled executor (Non-blocking)
    executor.submit(_safe_log, event)
