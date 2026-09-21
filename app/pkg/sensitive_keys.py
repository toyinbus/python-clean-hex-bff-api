"""Project-specific sensitive field names (this project's redaction contract).

The **generic mechanism** — the ``redact()`` function and the universal secret
keys (``password``, ``token``, ``authorization``, ...) — lives in
``app/utils/redact.py`` (the reusable library layer that knows nothing about
this project). THIS module holds the field names that are sensitive for *this*
project's business domains, so there is one place to audit what gets masked.

Usage — combine with the generic redactor at the call site (e.g. right before
logging a request/response body):

    from app.pkg import sensitive_keys
    from app.utils.redact import redact

    redact(
        payload,
        extra_keys=sensitive_keys.SENSITIVE_KEYS,     # -> [REDACTED]
        partial_keys=sensitive_keys.PARTIAL_KEYS,     # -> 4242***4242 (head+tail)
    )

Rules:
  * Match is by key name, case-insensitive.
  * ``SENSITIVE_KEYS`` are hidden fully (``[REDACTED]``). Use ``PARTIAL_KEYS``
    only for fields where keeping a short head + tail is useful and acceptable
    to show (the middle is always masked).
  * Add new field names here as domains grow; removing one stops masking that
    field, so do it deliberately.
  * Like ``pkg/error_codes``, this is pure data (frozensets) with no
    infrastructure dependency, so any layer may import it.
"""

from __future__ import annotations

# Fully hidden -> "[REDACTED]". Example project-specific field names; replace /
# extend these with the sensitive fields your own domains actually use.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "national_id",
        "id_card_number",
        "security_answer",
        "recovery_code",
    }
)

# Partially masked -> head + "***" + tail (e.g. "4242***4242"), kept for
# verification. Only put a field here when exposing its head/tail is acceptable.
PARTIAL_KEYS: frozenset[str] = frozenset(
    {
        "phone",
        "account_number",
        "email",
    }
)
