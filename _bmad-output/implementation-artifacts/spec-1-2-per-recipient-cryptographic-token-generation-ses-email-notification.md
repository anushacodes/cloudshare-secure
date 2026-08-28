---
title: "1.2 Per-Recipient Cryptographic Token Generation & SES Email Notification"
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

**Problem:** Sharing files via raw email parameters in URLs is vulnerable to link tampering, forwarding forgery, and unverified access tracking.

**Approach:** Generate an HMAC-SHA256 signed access token for each recipient email during upload, persist the token mapping in DynamoDB `FileMetadata.recipient_tokens`, and dispatch a personalized email to each recipient via AWS SES with their unique `/files/{file_id}/access?token={token}` link.

## Boundaries & Constraints

**Always:**
- Use cryptographic HMAC-SHA256 signatures with a secret key (`SECRET_KEY` / `TOKEN_SECRET`) to create unforgeable recipient tokens.
- Maintain isolated AWS credentials via environment variables; never hardcode secrets.
- In SES sandbox mode or if SES dispatch fails for an individual email, log the error clearly and allow the upload to succeed rather than crashing or corrupting database records.

**Ask First:**
- Custom HTML email templating beyond standard responsive notification format.

**Never:**
- Include raw unverified recipient email parameters without a valid cryptographic signature.
- Block or fail the entire upload process if a secondary notification email fails delivery.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Happy Path Dispatch | Upload with 2 recipients | Tokens generated, SES emails dispatched to both recipients | N/A |
| Token Signature Tampering | Altered token string | Token verification returns `None` / `False` | Reject access with HTTP 403 in access flow |
| SES Sandbox Email Rejection | Unverified recipient in SES sandbox | Log SES warning, record metadata in DynamoDB | Catch `ClientError` from SES and continue |

</frozen-after-approval>

## Code Map

- `backend/auth.py` -- Cryptographic token generation (`generate_recipient_token`) and verification (`verify_recipient_token`) using HMAC-SHA256
- `backend/ses_utils.py` -- AWS SES client and email dispatch helper (`send_recipient_email`)
- `backend/main.py` -- Update `POST /files/upload` to generate tokens, store in DynamoDB, and dispatch SES notifications
- `backend/tests/test_ses_tokens.py` -- Unit tests for token generation, tampering detection, and SES mock dispatch

## Tasks & Acceptance

**Execution:**
- [x] `backend/auth.py` -- Implement HMAC-SHA256 token helpers -- Provide `generate_recipient_token` and `verify_recipient_token`
- [x] `backend/ses_utils.py` -- Implement SES email dispatch module -- Provide `send_recipient_email` with HTML and text templates
- [x] `backend/main.py` -- Integrate token generation and SES dispatch into upload route -- Store `recipient_tokens` in DynamoDB and fire notifications
- [x] `backend/tests/test_ses_tokens.py` -- Add automated test suite -- Verify token security, signature validation, and mocked SES email dispatch

**Acceptance Criteria:**
- Given a file upload with recipient emails, when `POST /files/upload` is processed, then a unique signed token is generated for each recipient email and saved in `recipient_tokens` in DynamoDB.
- Given a generated recipient token, when verified against its `file_id` and secret, then it confirms authenticity and extracts the correct recipient email.
- Given a tampered or expired token, when verified, then verification fails.
- Given SES email dispatch, when executed, then personalized emails with access links are sent via AWS SES.

## Design Notes

Token format: `base64url(recipient_email + ":" + file_id + ":" + timestamp + ":" + hmac_sha256_signature)`

## Verification

**Commands:**
- `python3 backend/tests/test_unit.py` -- expected: All unit tests pass.

## Suggested Review Order

**Token Cryptography & Verification**

- HMAC-SHA256 token signing and tamper-proof verification helpers
  [`auth.py:10`](../../backend/auth.py#L10)

**Email Notification Dispatch**

- AWS SES client dispatch with HTML/text templates and error handling
  [`ses_utils.py:19`](../../backend/ses_utils.py#L19)

**Route Integration**

- Upload endpoint integration generating tokens and dispatching emails
  [`main.py:65`](../../backend/main.py#L65)

**Automated Tests**

- Unit test suite verifying token generation, tampering, and SES dispatch
  [`test_unit.py:18`](../../backend/tests/test_unit.py#L18)
