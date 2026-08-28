# Epic 1 Context: Secure File Upload and Recipient Distribution

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Enable uploaders to submit files with designated recipient email addresses, store files securely under private UUID-prefixed S3 keys, track metadata in DynamoDB, issue per-recipient cryptographically signed download links via AWS SES, and allow recipients to download files directly from S3 via short-lived presigned GET URLs.

## Stories

- Story 1.1: Backend Upload API with Presigned S3 Storage & DynamoDB Metadata
- Story 1.2: Per-Recipient Cryptographic Token Generation & SES Email Notification
- Story 1.3: Recipient Token Access & Presigned S3 Download Generation
- Story 1.4: Frontend Upload & Recipient Access User Interface

## Requirements & Constraints

- S3 bucket must block all direct public access; all file uploads/downloads must use short-lived presigned URLs.
- Access links must use cryptographically signed per-recipient tokens to prevent unauthorized forwarding or forged access tracking.
- Access tracking in DynamoDB must be append-only into `accessed_by`, ensuring duplicate accesses are idempotent.
- Frontend must never interact directly with AWS APIs or hold AWS credentials.

## Technical Decisions

- **Backend:** FastAPI (Python 3.10+) with `boto3` client, `pydantic` schemas, and `uvicorn`.
- **S3 Key Scheme:** `uploads/{file_id}/{original_filename}` where `file_id` is a UUID v4.
- **DynamoDB Schema:** `FileMetadata` table with partition key `file_id` (String). Attributes: `s3_key`, `original_filename`, `uploader_email`, `uploaded_at`, `content_type`, `size_bytes`, `recipients`, `accessed_by`, `recipient_tokens`.
- **SES Integration:** Async or helper-based email dispatch delivering HTML & text emails with personalized token links.

## UX & Interaction Patterns

- Upload form provides dynamic add/remove rows for recipient emails and client-side email format validation.
- Recipient download page validates access link on mount and provides clear download trigger and status feedback.

## Cross-Story Dependencies

- Story 1.1 establishes the upload API, S3 storage, and DynamoDB schema required by Story 1.2 (token generation) and Story 1.3 (access endpoint).
- Story 1.4 integrates the frontend against the verified APIs from 1.1, 1.2, and 1.3.
