"""
CyberSentinel AI — API Client
Author: CyberSentinel ML-LAB

Thin HTTP wrapper consumed by Streamlit dashboard pages.
All data flows through FastAPI — this module NEVER imports ML code.

Usage:
    from src.dashboard.api_client import get_api
    api = get_api()
    health = api.health()
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import requests
import streamlit as st

logger = logging.getLogger("dashboard.api_client")

API_URL = os.environ.get("API_URL", "http://localhost:8000")


class CyberSentinelAPI:
    """
    HTTP client for the CyberSentinel FastAPI server.

    Parameters
    ----------
    base_url : str
        Root URL of the FastAPI server (no trailing slash).
    timeout : float
        Request timeout in seconds.
    """

    def __init__(self, base_url: str = API_URL, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ----------------------------------------------------------------
    # GET endpoints (metadata — cached by Streamlit)
    # ----------------------------------------------------------------

    @st.cache_data(ttl=300, show_spinner=False)
    def health(_self) -> dict:
        """GET /health — pipeline and meta service status."""
        return _self._get("/health")

    @st.cache_data(ttl=300, show_spinner=False)
    def get_features(_self) -> dict:
        """GET /meta/features — feature names + importances."""
        return _self._get("/meta/features")

    @st.cache_data(ttl=300, show_spinner=False)
    def get_models(_self) -> dict:
        """GET /meta/models — binary, multiclass, preprocessing metadata."""
        return _self._get("/meta/models")

    @st.cache_data(ttl=300, show_spinner=False)
    def get_policy(_self) -> dict:
        """GET /meta/policy — deny/quarantine lists."""
        return _self._get("/meta/policy")

    @st.cache_data(ttl=300, show_spinner=False)
    def get_eval(_self) -> Optional[dict]:
        """GET /meta/eval — evaluation summary (None if 404)."""
        try:
            return _self._get("/meta/eval")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    @st.cache_data(ttl=300, show_spinner=False)
    def get_config(_self) -> dict:
        """GET /meta/config — training hyperparameters."""
        return _self._get("/meta/config")

    # ----------------------------------------------------------------
    # POST endpoints (inference — never cached)
    # ----------------------------------------------------------------

    def predict(self, features: dict[str, float]) -> dict:
        """POST /predict — single flow prediction."""
        return self._post("/predict", json={"features": features})

    def predict_batch(self, flows: list[dict[str, float]]) -> list[dict]:
        """POST /predict/batch — batch prediction."""
        return self._post("/predict/batch", json={"flows": flows})

    # ----------------------------------------------------------------
    # Private HTTP helpers
    # ----------------------------------------------------------------

    def _get(self, path: str) -> dict:
        """Issue a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict) -> dict | list:
        """Issue a POST request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        resp = requests.post(url, json=json, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def is_reachable(self) -> bool:
        """Check if the API server is reachable."""
        try:
            self.health()
            return True
        except Exception:
            return False


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------


@st.cache_resource
def get_api(base_url: str = API_URL) -> CyberSentinelAPI:
    """Return a cached API client instance (one per Streamlit session)."""
    return CyberSentinelAPI(base_url=base_url)
