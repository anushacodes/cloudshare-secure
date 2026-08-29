---
title: 'Refactor Previous Code to Comply with Python Engineering Standards'
type: 'refactor'
created: '2026-08-29'
status: 'done'
baseline_commit: '4d1b170e49242a125ff4ed212ab672df0f8abc0f'
review_loop_iteration: 0
context:
  - '{project-root}/Python Engineering Rulebook — Agent Coding Standards.md'
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Existing backend and lambda implementation code uses legacy typing (`typing.List`, `typing.Dict`, `typing.Optional`), scatters `os.getenv` calls across business logic, lacks module docstrings, has broad exception handling, and has test mocking that pollutes global `sys.modules`.

**Approach:** Centralize configuration via a cached `Settings` model in `backend/config.py`, update all Python modules to use modern Python 3.11+ type annotations and `from __future__ import annotations`, add structured module and function docstrings, refine error handling, isolate test mocks, and verify complete test suite execution.

## Boundaries & Constraints

**Always:**
- Use `from __future__ import annotations` and built-in generics (`list`, `dict`, `tuple`, `X | None`).
- Centralize environment configuration in `backend/config.py` using `@lru_cache` and `get_settings()`.
- Add module docstrings and explicit function docstrings to all backend and lambda modules.
- Ensure all existing functionality and API contracts (upload, recipient access, email dispatch, lambda auto-deletion) remain 100% backward-compatible.
- Run tests in isolation without mutating global `sys.modules` destructively.

**Ask First:**
- Any change to external HTTP route signatures or database schema keys.

**Never:**
- Commit credentials or `.env` files.
- Scatter direct `os.getenv` calls inside domain logic.
- Leave global mock pollution that prevents `pytest` from running test files together.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Configuration load | Environment variables set or default | `get_settings()` returns strongly-typed `Settings` instance | Raises `ValueError` or fallback to safe dev defaults |
| Token generation & verification | Valid `file_id` & `recipient_email` | Valid HMAC signature string, correct email returned on verify | Returns `None` on tampered signature or invalid base64 |
| Lifecycle deletion evaluation | Item with all recipients in `accessed_by` or older than hard expiry | `(True, reason)` tuple returned | Invalid date strings logged without crashing handler |
| Test suite run | `uv run --with-requirements backend/requirements.txt pytest` | All unit & integration tests run and pass without module pollution | Clean test execution |

</frozen-after-approval>

## Code Map

- `backend/config.py` -- Centralized application configuration with `@lru_cache` `get_settings()`.
- `backend/auth.py` -- HMAC recipient token generation and verification.
- `backend/s3_utils.py` -- S3 client access, upload helpers, and presigned URL generators.
- `backend/dynamo_utils.py` -- DynamoDB resource and table metadata operations.
- `backend/ses_utils.py` -- SES client and email dispatch helper.
- `backend/main.py` -- FastAPI application routes (`/health`, `/files/upload`, `/files/{file_id}/access`).
- `backend/tests/test_unit.py` -- Unit tests for auth, SES, S3, DynamoDB, and access endpoints.
- `backend/tests/test_upload.py` -- Moto integration tests for S3, DynamoDB, and upload endpoint.
- `lambda/lambda_function.py` -- Standalone lifecycle auto-deletion Lambda handler and `should_delete` logic.
- `lambda/test_lambda.py` -- Unit tests for lifecycle rules and lambda execution.
- `AGENTS.md` -- Repository agent instructions and coding standards reference.

## Tasks & Acceptance

**Execution:**
- [x] `backend/config.py` -- Create centralized settings module with `Settings` class, default values, and `@lru_cache def get_settings() -> Settings`.
- [x] `backend/auth.py` -- Refactor to modern typing (`str | None`), module docstrings, section comments, specific exception handling, and use `get_settings()`.
- [x] `backend/s3_utils.py` -- Refactor to modern typing, module docstrings, section comments, and use `get_settings()`.
- [x] `backend/dynamo_utils.py` -- Refactor to modern typing (`list[str]`, `dict[str, Any]`, `dict[str, Any] | None`), module docstrings, section comments, clean exception re-raising, and use `get_settings()`.
- [x] `backend/ses_utils.py` -- Refactor to modern typing, module docstrings, section comments, and use `get_settings()`.
- [x] `backend/main.py` -- Refactor to modern typing, module docstrings, section comments, and use `get_settings()`.
- [x] `lambda/lambda_function.py` -- Refactor to modern typing (`tuple[bool, str]`, `dict[str, Any]`), module docstrings, section comments, and centralized settings.
- [x] `backend/tests/test_unit.py` -- Clean up mock setup to prevent global `sys.modules` pollution across test suites.
- [x] `lambda/test_lambda.py` -- Clean up mock setup to prevent global `sys.modules` pollution.
- [x] `AGENTS.md` -- Document reference to coding regulations and rulebook.
- [x] Verification -- Run full test suites across `backend` and `lambda` to verify everything passes cleanly.

**Acceptance Criteria:**
- Given updated backend and lambda modules, when inspected, then all modules contain module docstrings, modern Python typing with `from __future__ import annotations`, and no direct un-cached `os.getenv` in business logic.
- Given the full test suite, when executed with `uv run --with-requirements backend/requirements.txt pytest`, then all unit and integration tests across backend and lambda pass cleanly without errors or module import conflicts.

## Design Notes

```python
# Centralized settings pattern
from __future__ import annotations
from functools import lru_cache
import os
from pydantic import BaseModel

class Settings(BaseModel):
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: str | None = os.getenv("AWS_SESSION_TOKEN")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "cloudshare-secure-bucket")
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "FileMetadata")
    SES_SENDER_EMAIL: str = os.getenv("SES_SENDER_EMAIL", "noreply@cloudshare.local")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cloudshare-insecure-dev-secret-key-change-me")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Verification

**Commands:**
- `uv run --with-requirements backend/requirements.txt pytest` -- expected: All backend and lambda tests pass with zero failures or errors.

## Suggested Review Order

**Centralized Configuration & Typing Standards**

- Centralized cached settings model for application-wide environment configuration.
  [`config.py:21`](../../backend/config.py#L21)

- Strict typing, module docstrings, and secret key retrieval from settings.
  [`auth.py:1`](../../backend/auth.py#L1)

- Settings integration and updated generic typing for S3 storage helpers.
  [`s3_utils.py:1`](../../backend/s3_utils.py#L1)

- Modern type annotations, safe access tracking, and settings injection for DynamoDB.
  [`dynamo_utils.py:1`](../../backend/dynamo_utils.py#L1)

- Settings-based client creation and HTML escaping for recipient email notifications.
  [`ses_utils.py:1`](../../backend/ses_utils.py#L1)

**API Endpoints & Auto-Deletion Lambda**

- Refactored FastAPI routes with modern typing and centralized URL configuration.
  [`main.py:1`](../../backend/main.py#L1)

- Standalone Lambda lifecycle handler with settings dataclass and timezone-aware checks.
  [`lambda_function.py:1`](../../lambda/lambda_function.py#L1)

**Test Isolation & Configuration**

- Clean `unittest.mock.patch` isolation without polluting global `sys.modules`.
  [`test_unit.py:1`](../../backend/tests/test_unit.py#L1)

- Unit tests for Lambda deletion conditions and execution.
  [`test_lambda.py:1`](../../lambda/test_lambda.py#L1)

- Integration tests for S3 and DynamoDB with Moto.
  [`test_upload.py:1`](../../backend/tests/test_upload.py#L1)

- Pytest module resolution configuration for root execution.
  [`pytest.ini:1`](../../pytest.ini#L1)

