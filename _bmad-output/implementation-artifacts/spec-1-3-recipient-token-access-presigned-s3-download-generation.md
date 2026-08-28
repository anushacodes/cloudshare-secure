---
title: "1.3 Recipient Token Access & Presigned S3 Download Generation"
type: "feature"
created: "2026-08-28"
baseline_commit: "e89c8c5"
status: "done"
review_loop_iteration: 0
context:
  - "{project-root}/AGENTS.md"
  - "{project-root}/_bmad-output/specs/spec-cloudshare-secure/stack.md"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Recipients need a frictionless way to access and download shared files without creating an account, while the backend cryptographically verifies the link and logs access in DynamoDB to drive the completion-based auto-deletion lifecycle.

**Approach:** Implement `GET /files/{file_id}/access?token={token}` to validate the recipient token, idempotently append the recipient email to DynamoDB `accessed_by`, and generate a short-lived presigned S3 GET URL.

## Boundaries & Constraints

**Always:**
- Cryptographically verify the recipient token signature and ensure the token matches the requested `file_id`.
- Ensure access recording in DynamoDB is idempotent (never append duplicate emails to `accessed_by`).
- Generate presigned S3 GET URLs with a short lifespan (default: 300 seconds / 5 minutes).
- Return HTTP 403 for tampered or invalid tokens; return HTTP 404 if file does not exist.

**Ask First:**
- Automatic HTTP 307 temporary redirect to the presigned S3 URL vs. returning a JSON payload containing the download URL and file metadata. (We provide JSON with `download_url` and support optional direct redirect with `?redirect=true`).

**Never:**
- Allow downloads if token verification fails.
- Require recipients to register or provide login credentials.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Valid Token First Access | `GET /files/{file_id}/access?token={valid_token}` | HTTP 200 with `download_url`, `original_filename`, `size_bytes`, logs access in DynamoDB | N/A |
| Repeated Access (Same Recipient) | Same valid token called again | HTTP 200 with fresh `download_url`, DynamoDB `accessed_by` remains single copy | Idempotent |
| Tampered / Invalid Token | `GET /files/{file_id}/access?token=invalid_sig` | HTTP 403 Forbidden | Return `{ "detail": "Invalid or expired access token" }` |
| Non-Existent File ID | `GET /files/non-existent-uuid/access?token={any}` | HTTP 404 Not Found | Return `{ "detail": "File not found" }` |

</frozen-after-approval>

## Code Map

- `backend/auth.py` -- Token verification helper (`verify_recipient_token`)
- `backend/dynamo_utils.py` -- Access recording helper (`add_recipient_access`, `get_file_metadata`)
- `backend/s3_utils.py` -- Presigned GET generator (`generate_presigned_get_url`)
- `backend/main.py` -- Implement `GET /files/{file_id}/access` route handler
- `backend/tests/test_unit.py` -- Add unit tests for access route and access idempotency

## Tasks & Acceptance

**Execution:**
- [x] `backend/main.py` -- Implement `GET /files/{file_id}/access` endpoint -- Validate token, log access in DynamoDB, and return presigned S3 GET URL
- [x] `backend/tests/test_unit.py` -- Add comprehensive test cases for access endpoint -- Verify happy path, repeated access idempotency, invalid token 403, and missing file 404

**Acceptance Criteria:**
- Given a recipient calling `GET /files/{file_id}/access?token={valid_token}`, when verified, then the recipient email is appended to `accessed_by` in DynamoDB, and a JSON response with presigned `download_url`, `original_filename`, `content_type`, and `size_bytes` is returned.
- Given an invalid, tampered, or mismatched token, when sent to the access endpoint, then HTTP 403 Forbidden is returned.
- Given multiple calls from the same recipient, when access is recorded, then DynamoDB `accessed_by` contains the recipient email only once.

## Verification

**Commands:**
- `python3 backend/tests/test_unit.py` -- expected: All unit tests pass.

## Suggested Review Order

**Access Route Handler**

- Recipient token validation, DynamoDB access recording, and presigned S3 URL generation
  [`main.py:126`](../../backend/main.py#L126)

**DynamoDB Idempotency Logic**

- Append-only `accessed_by` list helper avoiding duplicate access entries
  [`dynamo_utils.py:65`](../../backend/dynamo_utils.py#L65)

**Automated Tests**

- Unit tests for access endpoint validation, 403 invalid token, and 404 missing file
  [`test_unit.py:150`](../../backend/tests/test_unit.py#L150)
