---
id: SPEC-cloudshare-secure
companions:
  - architecture-diagrams.md
  - stack.md
sources:
  - docs/ARCHITECTURE.md
  - docs/STEPS.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# CloudShare Secure

## Why

Traditional file-sharing tools either leave shared files in cloud storage indefinitely or rely on arbitrary, fixed time expiration. CloudShare Secure solves this with a completion-based lifecycle: uploaded files are shared with designated recipients via per-recipient signed links, and automatically purged from storage the moment all designated recipients have accessed them.

## Capabilities

- **CAP-1**
  - **intent:** User can upload a file and specify a list of recipient email addresses to share the file securely.
  - **success:** File is uploaded to S3 under a UUID-prefixed key, metadata record is created in DynamoDB with the recipient list and empty `accessed_by`, and an SES email is sent to each recipient containing a unique signed access link.

- **CAP-2**
  - **intent:** Recipient can access and download their assigned file using their unique signed link without needing an account.
  - **success:** Backend validates the signed token, appends the recipient's email to `accessed_by` in DynamoDB if not previously recorded, and returns a short-lived presigned S3 GET URL for direct file download.

- **CAP-3**
  - **intent:** System automatically purges files and metadata as soon as all designated recipients have completed their access, or when reaching fallback hard expiry.
  - **success:** Scheduled Lambda function scans DynamoDB, detects items where `set(recipients) == set(accessed_by)` OR `uploaded_at` exceeds a 30-day fallback threshold, deletes the corresponding S3 object, and deletes the DynamoDB item.

- **CAP-4**
  - **intent:** Authenticated uploader can view the access progress of their shared files and revoke/delete them early.
  - **success:** Uploader authenticates via JWT/Cognito to view a dashboard listing uploaded files with per-recipient access status, and can trigger immediate deletion via `DELETE /files/{file_id}`.

## Constraints

- Direct public access to the S3 bucket is completely blocked; all transfers must use short-lived presigned URLs.
- Access links must be cryptographically signed per-recipient so a forwarded link cannot falsely register another recipient's access.
- Frontend must never interact with AWS directly or hold AWS credentials; all AWS operations are routed through the backend or handled by the scheduled Lambda function.
- The deletion engine must be decoupled from the API backend, running as an independent scheduled Lambda triggered via EventBridge.

## Non-goals

- General-purpose long-term cloud storage or sync drive.
- In-place multi-user document collaboration or live editing.
- Anonymous unverified public file drops.

## Success signal

- An uploader shares a file with multiple recipients; as soon as the final recipient downloads the file, the next scheduled Lambda execution cleanly purges the file from S3 and DynamoDB without manual intervention.

## Assumptions

- Lambda schedule frequency of every 10–15 minutes provides sufficient deletion timeliness for standard sharing workloads.
- Uploader authentication uses JWT bearer tokens for Phase 1/2 with optional AWS Cognito migration.
