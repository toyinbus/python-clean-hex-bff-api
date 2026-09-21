# Conventions — python-clean-hex-bff-api

Service-specific rules. Architecture-wide rules live in `ARCHITECTURE.md`
(the CleanHex guide). Read that first. This project is a **generic, reusable
reference** — copy it as a starting point for any FastAPI BFF.

## 1. Layer & naming (summary)

- CleanHex feature layout: `domain/entity`, `domain/port`, `usecase`,
  `delivery/http` (+ `dto`), `infra/db` (+ `model`), `infra/service`.
- Implementations are `*Impl` classes bound to their port ABC in `set.py`.
- One word per feature folder (`user`), snake_case files, PascalCase classes,
  snake_case methods, UPPER_SNAKE constants.

## 2. BFF role

- This is a **BFF** (Backend-for-Frontend): client-facing. It validates the
  client request, calls downstream capabilities (databases, domain services,
  third-party APIs — mocked here), and shapes the response for one audience.
- Keep the BFF thin: no cross-cutting domain writes belong here that a shared
  domain service should own. A BFF should not call another BFF.
- Keep BFF code deployment-agnostic: no cloud-vendor or edge-stack names in
  source or `.env`.

## 3. Dependency injection

- Use the `dependency-injector` container. Each feature owns a `set.py`
  (`{X}Container` + `{X}Feature`); the composition root is `app/di/container.py`.
- Feature code never imports `app.pkg.config` — config primitives are extracted
  at the DI boundary and injected into constructors.

## 4. HTTP & responses

- Every response uses `app/utils/response.py` (`response_success` /
  `response_error`) and carries a 5-digit `code` + `request_id`.
- Frontends map `code` → i18n; they never string-match `message`.
- New codes are appended to `app/utils/apperror.py` (append-only, never reuse).
- Format validation lives in pydantic DTOs; business validation in the usecase.

## 5. Database (demo)

- The demo `user` repository is **mocked in-memory** — no real DB is required.
- A real repository would map DB models ↔ entities at the boundary and translate
  driver errors into `AppError` (never leak infra errors to the usecase).
- Swapping the mock for a real backend is a one-line change in `set.py` (bind a
  different `*Impl` to the repository port) — no usecase/handler edits.

## 6. Language

- English only, everywhere (comments, docs, commit messages).
- Prefer neutral, non-ambiguous domain vocabulary.

## 7. Testing

- `pytest` + function-field mocks, unit tests only (no real infra).
- Mirror the source tree under `tests/`; test files end with `_test.py`.
