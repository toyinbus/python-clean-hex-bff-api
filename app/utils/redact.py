"""Redact sensitive values before they are logged or returned to a client.

Generic, reusable (knows nothing about this project's domain). Use it anywhere a
dict/list that may contain secrets is about to be serialized into a log line or
a response body.

Two masking styles:

  * **Full** (default) — the value is completely hidden behind a clear label so
    it is obvious it was removed:

        redact({"password": "hunter2"})     -> {"password": "[REDACTED]"}

  * **Partial** — for keys you pass in ``partial_keys``, the head and tail are
    kept (the middle is masked) so you can still eyeball / verify it, e.g. a card
    or phone:

        redact({"card": "4242424242424242"}, partial_keys={"card"})
        -> {"card": "4242***4242"}

The match is by key name (case-insensitive). Only **universal** secret keys live
here; **project-specific** field names belong in ``app/pkg/sensitive_keys.py``
and are supplied per call via ``extra_keys`` / ``partial_keys`` (this module
never imports ``pkg``, so it stays reusable):

    from app.pkg import sensitive_keys
    redact(payload, extra_keys=sensitive_keys.SENSITIVE_KEYS)
"""

from __future__ import annotations

from typing import Any

FULL_MASK = "[REDACTED]"
PARTIAL_INFIX = "***"

# Common secret-bearing field names. Kept deliberately broad; add project- or
# feature-specific names at the call site via `extra_keys`.
DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "apikey",
        "otp",
        "pin",
        "card_number",
        "cvv",
    }
)


def _partial_mask(value: Any, visible: int) -> str:
    """Keep the first and last ``visible`` characters, mask the middle.

    Falls back to a full mask when the value is too short to show both a head
    and a tail without exposing (almost) the whole thing.
    """
    text = str(value)
    if len(text) <= visible * 2:
        return FULL_MASK
    return f"{text[:visible]}{PARTIAL_INFIX}{text[-visible:]}"


def redact(
    value: Any,
    *,
    extra_keys: frozenset[str] | set[str] | None = None,
    partial_keys: frozenset[str] | set[str] | None = None,
    visible: int = 4,
) -> Any:
    """Return a copy of ``value`` with sensitive dict entries masked.

    Recurses through nested dicts and lists/tuples. Non-container values are
    returned unchanged.

    * Keys in the full set (defaults + ``extra_keys``) become ``[REDACTED]``.
    * Keys in ``partial_keys`` keep their first/last ``visible`` chars
      (``4242***4242``); the middle is masked.
    * Full masking wins if a key somehow appears in both.
    """
    full = DEFAULT_SENSITIVE_KEYS | {k.lower() for k in extra_keys} if extra_keys else DEFAULT_SENSITIVE_KEYS
    partial = {k.lower() for k in partial_keys} if partial_keys else frozenset()

    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            result: dict[Any, Any] = {}
            for key, val in node.items():
                lkey = key.lower() if isinstance(key, str) else None
                if lkey is not None and lkey in full:
                    result[key] = FULL_MASK
                elif lkey is not None and lkey in partial:
                    result[key] = _partial_mask(val, visible)
                else:
                    result[key] = _walk(val)
            return result
        if isinstance(node, (list, tuple)):
            return [_walk(item) for item in node]
        return node

    return _walk(value)
