"""
CyberSentinel AI
Machine Learning Intrusion Detection System

Policy Mapper (Stage 6)
Author: CyberSentinel ML-LAB

Converts raw model predictions into structured, actionable firewall / SOC
decisions.

Decision Rules
--------------
    binary == 0                          → PolicyAction.ALLOW
    binary == 1 AND attack in deny_list  → PolicyAction.DENY
    binary == 1 AND attack not in deny   → PolicyAction.QUARANTINE

The quarantine / deny split is driven entirely by configs/policy.yaml,
which SOC analysts can update without touching code.

Output
------
Every call to map_prediction() returns a PolicyDecision dataclass:

    PolicyDecision(
        action         = "ALLOW" | "QUARANTINE" | "DENY"
        binary_pred    = 0 | 1
        attack_type    = "DDoS" | None
        confidence     = 0.97          # binary model probability for predicted class
        attack_proba   = {"DDoS": 0.9, "PortScan": 0.05, ...} | None
        timestamp      = "2026-03-25T21:24:00+05:30"
        reason         = human-readable explanation string
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("policy_mapper")

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

from src.core.paths import CONFIGS_DIR

POLICY_CONFIG_PATH = CONFIGS_DIR / "policy.yaml"


# ------------------------------------------------------------------
# Policy action enum
# ------------------------------------------------------------------


class PolicyAction(str, Enum):
    """Possible firewall / SOC actions."""

    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


# ------------------------------------------------------------------
# PolicyDecision dataclass
# ------------------------------------------------------------------


@dataclass
class PolicyDecision:
    """
    Structured result of a single policy evaluation.

    Attributes
    ----------
    action : PolicyAction
        The recommended firewall / SOC action.
    binary_pred : int
        Raw binary model prediction (0 = Benign, 1 = Attack).
    confidence : float
        Probability score for the binary prediction (0.0–1.0).
    attack_type : str | None
        Attack class name from the multi-class model (None when benign).
    attack_proba : dict[str, float] | None
        Full probability distribution over attack classes (None when benign).
    timestamp : str
        ISO-8601 UTC timestamp of the decision.
    reason : str
        Human-readable explanation for the chosen action.
    """

    action: PolicyAction
    binary_pred: int
    confidence: float
    attack_type: Optional[str] = None
    attack_proba: Optional[dict[str, float]] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reason: str = ""

    def to_dict(self) -> dict:
        """Serialise to a plain dict (action converted to string)."""
        d = asdict(self)
        d["action"] = self.action.value
        return d

    def __str__(self) -> str:
        atk = f"  Attack: {self.attack_type}" if self.attack_type else ""
        return (
            f"[{self.action.value}] binary={self.binary_pred} "
            f"conf={self.confidence:.3f}{atk} | {self.reason}"
        )


# ------------------------------------------------------------------
# Policy config loader
# ------------------------------------------------------------------


def _load_policy_config() -> dict:
    """
    Load configs/policy.yaml.

    Returns a dict with keys:
        deny_classes       : list[str]   — high-risk; always DENY
        quarantine_classes : list[str]   — low-risk; always QUARANTINE
        default_attack_action : str      — used when attack type not in either list
    """
    if not POLICY_CONFIG_PATH.exists():
        logger.warning(
            "policy.yaml not found at %s — using built-in defaults.", POLICY_CONFIG_PATH
        )
        return _default_policy()
    with open(POLICY_CONFIG_PATH, "r") as fh:
        cfg = yaml.safe_load(fh) or {}
    return cfg.get("policy", _default_policy())


def _default_policy() -> dict:
    """Hard-coded fallback matching CICIDS2017 labels."""
    return {
        "deny_classes": [
            "DDoS",
            "DoS GoldenEye",
            "DoS Hulk",
            "DoS Slowhttptest",
            "DoS slowloris",
            "PortScan",
            "FTP-Patator",
            "SSH-Patator",
            "Bot",
        ],
        "quarantine_classes": [
            "Web Attack – Brute Force",
            "Web Attack – XSS",
            "Web Attack – Sql Injection",
            "Infiltration",
            "Heartbleed",
        ],
        "default_attack_action": "QUARANTINE",
    }


# ------------------------------------------------------------------
# PolicyMapper class
# ------------------------------------------------------------------


class PolicyMapper:
    """
    Maps model predictions to policy decisions.

    Instantiate once and reuse across multiple predictions to avoid
    reloading the config file on every call.

    Parameters
    ----------
    config_path : Path, optional
        Override path to policy.yaml.

    Examples
    --------
    >>> mapper = PolicyMapper()
    >>> decision = mapper.map_prediction(
    ...     binary_pred=1,
    ...     binary_confidence=0.97,
    ...     attack_type="DDoS",
    ...     attack_proba={"DDoS": 0.93, "PortScan": 0.05},
    ... )
    >>> print(decision)
    [DENY] binary=1 conf=0.970  Attack: DDoS | High-risk attack type: DDoS
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        cfg = _load_policy_config() if config_path is None else self._load(config_path)
        # Normalise to lowercase for case-insensitive matching
        self._deny: frozenset[str] = frozenset(
            c.strip().lower() for c in cfg.get("deny_classes", [])
        )
        self._quarantine: frozenset[str] = frozenset(
            c.strip().lower() for c in cfg.get("quarantine_classes", [])
        )
        self._default_attack_action: str = cfg.get(
            "default_attack_action", "QUARANTINE"
        ).upper()
        logger.info(
            "PolicyMapper loaded — deny=%d classes  quarantine=%d classes  default=%s",
            len(self._deny),
            len(self._quarantine),
            self._default_attack_action,
        )

    @staticmethod
    def _load(path: Path) -> dict:
        with open(path, "r") as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("policy", _default_policy())

    # ---- core decision logic ----------------------------------------

    def map_prediction(
        self,
        binary_pred: int,
        binary_confidence: float,
        attack_type: Optional[str] = None,
        attack_proba: Optional[dict[str, float]] = None,
    ) -> PolicyDecision:
        """
        Convert model output into a PolicyDecision.

        Parameters
        ----------
        binary_pred : int
            Output of binary classifier (0 = Benign, 1 = Attack).
        binary_confidence : float
            Probability of the predicted binary class.
        attack_type : str, optional
            Attack class name from multi-class model.
            Required when binary_pred == 1; ignored when binary_pred == 0.
        attack_proba : dict[str, float], optional
            Full probability dict from multi-class model.
            Keys are attack class names, values are probabilities.

        Returns
        -------
        PolicyDecision
        """
        if binary_pred == 0:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                binary_pred=0,
                confidence=round(binary_confidence, 6),
                attack_type=None,
                attack_proba=None,
                reason="Traffic classified as benign.",
            )

        # binary == 1 → determine action from attack type
        action, reason = self._resolve_attack_action(attack_type)

        return PolicyDecision(
            action=action,
            binary_pred=1,
            confidence=round(binary_confidence, 6),
            attack_type=attack_type,
            attack_proba={k: round(v, 6) for k, v in attack_proba.items()}
            if attack_proba
            else None,
            reason=reason,
        )

    def _resolve_attack_action(
        self, attack_type: Optional[str]
    ) -> tuple[PolicyAction, str]:
        """Return (PolicyAction, reason_string) for a detected attack."""
        if attack_type is None:
            # Binary flagged as attack but no multi-class prediction available
            fallback = PolicyAction(self._default_attack_action)
            return (
                fallback,
                "Attack detected; attack type unavailable — applying default policy.",
            )

        normalised = attack_type.strip().lower()

        if normalised in self._deny:
            return (
                PolicyAction.DENY,
                f"High-risk attack type: {attack_type}",
            )
        if normalised in self._quarantine:
            return (
                PolicyAction.QUARANTINE,
                f"Low-risk attack type: {attack_type} — isolating for investigation.",
            )

        # Not in either explicit list → apply configurable default
        fallback = PolicyAction(self._default_attack_action)
        return (
            fallback,
            f"Attack type '{attack_type}' not in policy lists — applying default: {fallback.value}.",
        )

    # ---- batch convenience ------------------------------------------

    def map_batch(
        self,
        binary_preds: list[int],
        binary_confidences: list[float],
        attack_types: Optional[list[Optional[str]]] = None,
        attack_probas: Optional[list[Optional[dict[str, float]]]] = None,
    ) -> list[PolicyDecision]:
        """
        Map a batch of predictions to policy decisions.

        Parameters
        ----------
        binary_preds : list[int]
        binary_confidences : list[float]
        attack_types : list[str | None], optional
        attack_probas : list[dict | None], optional

        Returns
        -------
        list[PolicyDecision]
        """
        n = len(binary_preds)
        attack_types = attack_types or [None] * n
        attack_probas = attack_probas or [None] * n

        return [
            self.map_prediction(bp, bc, at, ap)
            for bp, bc, at, ap in zip(
                binary_preds, binary_confidences, attack_types, attack_probas
            )
        ]

    # ---- introspection ----------------------------------------------

    def get_deny_classes(self) -> list[str]:
        """Return the current DENY class list (original case from config)."""
        return sorted(self._deny)

    def get_quarantine_classes(self) -> list[str]:
        """Return the current QUARANTINE class list (original case from config)."""
        return sorted(self._quarantine)

    def describe(self) -> None:
        """Print a human-readable summary of the current policy."""
        print("\n" + "=" * 55)
        print("  CyberSentinel-AI — Active Policy Table")
        print("=" * 55)
        print(f"  {'ALLOW':12s}  binary == 0  (Benign traffic)")
        print(f"\n  {'DENY':12s}  binary == 1  +  attack in:")
        for cls in sorted(self._deny):
            print(f"               • {cls}")
        print(f"\n  {'QUARANTINE':12s}  binary == 1  +  attack in:")
        for cls in sorted(self._quarantine):
            print(f"               • {cls}")
        print(f"\n  Default for unknown attack types: {self._default_attack_action}")
        print("=" * 55)

    def apply_zero_trust(self, attack_type: Optional[str], trust_score: float, risk_level: str) -> str:
        """
        Final authority for policy decisions in Enterprise Zero-Trust mode.
        """
        if risk_level == "HIGH":
            return "DENY"
        elif risk_level == "MEDIUM":
            return "QUARANTINE"
        elif risk_level == "LOW" and attack_type and attack_type.upper() != "BENIGN":
            return "MONITOR"
        else:
            return "ALLOW"


# ------------------------------------------------------------------
# Module-level convenience function
# ------------------------------------------------------------------


def map_prediction(
    binary_pred: int,
    binary_confidence: float,
    attack_type: Optional[str] = None,
    attack_proba: Optional[dict[str, float]] = None,
) -> PolicyDecision:
    """
    Module-level convenience wrapper around PolicyMapper.

    Creates a disposable PolicyMapper each call (reloads config).
    For repeated calls, instantiate PolicyMapper() once and reuse.

    Parameters
    ----------
    binary_pred : int
    binary_confidence : float
    attack_type : str | None
    attack_proba : dict | None

    Returns
    -------
    PolicyDecision
    """
    mapper = PolicyMapper()
    return mapper.map_prediction(
        binary_pred, binary_confidence, attack_type, attack_proba
    )


# ------------------------------------------------------------------
# CLI — quick sanity checks
# ------------------------------------------------------------------

if __name__ == "__main__":
    mapper = PolicyMapper()
    mapper.describe()

    print("\n--- Example decisions ---\n")

    cases = [
        (0, 0.99, None, None),
        (1, 0.95, "DDoS", {"DDoS": 0.92, "PortScan": 0.05}),
        (1, 0.88, "Heartbleed", {"Heartbleed": 0.80, "Infiltration": 0.12}),
        (1, 0.76, "Web Attack – XSS", {"Web Attack – XSS": 0.70}),
        (1, 0.82, "Bot", {"Bot": 0.78, "DDoS": 0.10}),
        (1, 0.71, "UnknownAttack", {"UnknownAttack": 0.65}),
    ]

    for bp, bc, at, ap in cases:
        decision = mapper.map_prediction(bp, bc, at, ap)
        print(f"  {decision}")
