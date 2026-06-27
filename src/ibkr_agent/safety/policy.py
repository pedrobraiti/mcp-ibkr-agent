"""Backwards-compatible shim — the guard now lives in ``trading_core.safety.policy``.

New code should import from ``trading_core.safety.policy``.
"""

from trading_core.safety.policy import GuardedBroker, SafetyError

__all__ = ["GuardedBroker", "SafetyError"]
