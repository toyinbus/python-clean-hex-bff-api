"""Project-specific response codes (this project's domain contract).

The **generic mechanism** — the ``AppError`` classes, the resolver, and the
cross-cutting ``10xxx`` codes — lives in ``app/utils/apperror.py`` (the reusable
library layer that knows nothing about this project). THIS module holds the codes
that are specific to *this* project's business domains.

Keeping every project code in one append-only registry gives the frontend a
single source of truth (it maps ``code`` -> i18n) and guarantees numbers never
collide across features.

Rules:
  * Append-only. Never reuse or renumber a code once it has shipped.
  * Reserve one 5-digit block per business domain (see the ranges below).
  * A feature raises a generic ``AppError`` subclass and passes the domain code:
    ``raise AlreadyExistsError("email already registered",
                               code=error_codes.USER_EMAIL_TAKEN)``.

Ranges (add new numbers at the end of the matching block):
  20xxx  auth
  30xxx  billing
  70xxx  user
"""

from __future__ import annotations

# ── User (70xxx) ────────────────────────────────────────────────────────────
USER_EMAIL_TAKEN = "70001"
