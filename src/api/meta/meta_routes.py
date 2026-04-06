"""
CyberSentinel AI — Meta Routes
Author: CyberSentinel ML-LAB

Read-only GET endpoints that serve cached metadata.
All data comes from MetaService (loaded at startup) — zero disk I/O per request.
"""

import logging
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger("meta_routes")

from src.api.meta.meta_schemas import (
    FeaturesResponse,
    ModelsResponse,
    PolicyResponse,
    EvalResponse,
    ConfigResponse,
)

meta_router = APIRouter(tags=["meta"])


class _FallbackMetaService:
    """Safe fallback for MetaStore during startup/failure."""
    def get_features(self): return {"features": [], "status": "missing"}
    def get_models(self): return {"status": "missing"}
    def get_policy(self): return {"status": "missing"}
    def get_eval(self): return {"f1_macro": 0.0, "status": "missing"}
    def get_config(self): return {"status": "missing"}


def _get_meta_service(request):
    """Retrieve the startup-loaded MetaService from app state. Never fails with 503."""
    svc = getattr(request.app.state, "meta_service", None)
    if svc is None:
        # Zero-Failure Policy: Return a module-level fallback object if not loaded
        logger.error("MetaService not found in app state! Using emergency fallback.")
        return _FallbackMetaService()
    return svc


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@meta_router.get(
    "/features",
    response_model=FeaturesResponse,
    summary="Selected features and importances",
)
def get_features(request: Request):
    """Feature list (40 names) + top-20 importances for binary and multiclass models."""
    svc = _get_meta_service(request)
    return svc.get_features()


@meta_router.get("/models", response_model=ModelsResponse, summary="Model metadata")
def get_models(request: Request):
    """Model type, classes, training config, data stats, and validation metrics."""
    svc = _get_meta_service(request)
    return svc.get_models()


@meta_router.get(
    "/policy", response_model=PolicyResponse, summary="Active policy configuration"
)
def get_policy(request: Request):
    """Deny list, quarantine list, and default action."""
    svc = _get_meta_service(request)
    return svc.get_policy()


@meta_router.get("/eval", response_model=EvalResponse, summary="Evaluation metrics")
def get_eval(request: Request):
    """Binary + multiclass evaluation summary. Enforces 'missing' status fallback."""
    svc = _get_meta_service(request)
    return svc.get_eval()


@meta_router.get(
    "/config", response_model=ConfigResponse, summary="Training hyperparameters"
)
def get_config(request: Request):
    """Feature selection, binary training, and multiclass training configuration."""
    svc = _get_meta_service(request)
    return svc.get_config()
