"""
CyberSentinel AI — Meta Routes
Author: CyberSentinel ML-LAB

Read-only GET endpoints that serve cached metadata.
All data comes from MetaService (loaded at startup) — zero disk I/O per request.
"""

from fastapi import APIRouter, HTTPException

from src.api.meta.meta_schemas import (
    FeaturesResponse,
    ModelsResponse,
    PolicyResponse,
    EvalResponse,
    ConfigResponse,
)

meta_router = APIRouter(tags=["meta"])


def _get_meta_service():
    """Retrieve the startup-loaded MetaService from main.py."""
    from src.api.main import meta_service

    if meta_service is None:
        raise HTTPException(
            status_code=503,
            detail="MetaService not loaded yet. Server is still starting.",
        )
    return meta_service


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@meta_router.get(
    "/features",
    response_model=FeaturesResponse,
    summary="Selected features and importances",
)
def get_features():
    """Feature list (40 names) + top-20 importances for binary and multiclass models."""
    svc = _get_meta_service()
    return svc.get_features()


@meta_router.get("/models", response_model=ModelsResponse, summary="Model metadata")
def get_models():
    """Model type, classes, training config, data stats, and validation metrics."""
    svc = _get_meta_service()
    return svc.get_models()


@meta_router.get(
    "/policy", response_model=PolicyResponse, summary="Active policy configuration"
)
def get_policy():
    """Deny list, quarantine list, and default action."""
    svc = _get_meta_service()
    return svc.get_policy()


@meta_router.get("/eval", response_model=EvalResponse, summary="Evaluation metrics")
def get_eval():
    """Binary + multiclass evaluation summary. Returns 404 if eval has not been run."""
    svc = _get_meta_service()
    data = svc.get_eval()
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not run yet. Run `python src/models/evaluator.py` first.",
        )
    return data


@meta_router.get(
    "/config", response_model=ConfigResponse, summary="Training hyperparameters"
)
def get_config():
    """Feature selection, binary training, and multiclass training configuration."""
    svc = _get_meta_service()
    return svc.get_config()
