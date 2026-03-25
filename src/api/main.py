"""
CyberSentinel AI — API Server
Author: CyberSentinel ML-LAB

FastAPI entry point for the CyberSentinel intrusion detection system.
"""
from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="CyberSentinel AI",
    description="Machine Learning Intrusion Detection System API",
    version="1.0.0"
)

# Include the inference endpoints
app.include_router(router)

@app.get("/health", summary="Health Check")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "CyberSentinel AI API"}

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
