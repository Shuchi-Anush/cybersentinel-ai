"""
CyberSentinel AI — meta sub-package

Public API
----------
    from src.api.meta import meta_router, MetaService
"""

from src.api.meta.meta_routes import meta_router
from src.api.meta.meta_service import MetaService

__all__ = ["meta_router", "MetaService"]
