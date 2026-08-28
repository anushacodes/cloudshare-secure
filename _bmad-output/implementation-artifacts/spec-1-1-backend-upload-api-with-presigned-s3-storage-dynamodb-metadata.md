---
title: "1.1 Backend Upload API with Presigned S3 Storage & DynamoDB Metadata"
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

**Problem:** Users need a backend service to upload files securely to AWS S3 with private access and store file sharing metadata in DynamoDB.

**Approach:** Implement the core FastAPI application with Boto3 helper modules (`s3_utils.py` and `dynamo_utils.py`), environment configuration via `.env`, and the `POST /files/upload` endpoint to ingest files and initialize `FileMetadata` records.

## Boundaries & Constraints

**Always:**
- Keep all S3 bucket access private; transfers use presigned URLs or backend Boto3 calls with IAM credentials loaded from gitignored `.env`.
- Use UUID-prefixed S3 keys formatted as `uploads/{file_id}/{original_filename}`.
- Store initial `accessed_by` as an empty list in DynamoDB and use `ExpressionAttributeNames` for any reserved keywords.
- Include unit/integration tests with mocked AWS services (`moto` / `unittest.mock`).

**Ask First:**
- Switching from server-side upload handling to direct client-side presigned PUT upload.

**Never:**
- Hardcode AWS credentials in source code or commit `.env`.
- Allow direct public S3 access or unvalidated file paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Happy Path Upload | Multipart file + recipient emails list | HTTP 200 with `file_id`, `s3_key`, `original_filename`, `recipients` | N/A |
| Empty Recipient List | Multipart file + empty recipients `[]` | HTTP 422 / 400 Bad Request | Return `{ "detail": "At least one recipient email is required" }` |
| Missing File Payload | Request with no file attached | HTTP 422 Unprocessable Entity | FastAPI standard validation error |
| S3 Upload Service Failure | AWS S3 client raises ClientError | HTTP 500 Internal Server Error | Log error and return clean error response without orphaned records |

</frozen-after-approval>

## Code Map

- `backend/requirements.txt` -- Python dependencies (`fastapi`, `uvicorn`, `boto3`, `python-dotenv`, `python-multipart`, `pytest`, `httpx`, `moto`)
- `backend/s3_utils.py` -- S3 client initialization, presigned URL generation, and upload/delete operations
- `backend/dynamo_utils.py` -- DynamoDB client initialization and `FileMetadata` CRUD operations
- `backend/main.py` -- FastAPI application, CORS middleware, `/health`, and `POST /files/upload` route
- `backend/tests/test_upload.py` -- Automated unit & route integration tests with mocked S3 and DynamoDB

## Tasks & Acceptance

**Execution:**
- [x] `backend/requirements.txt` -- Add required backend dependencies -- Ensure runtime and test libraries are specified
- [x] `backend/s3_utils.py` -- Implement S3 client helpers -- Provide `upload_file_to_s3`, `generate_presigned_get_url`, and `generate_presigned_put_url`
- [x] `backend/dynamo_utils.py` -- Implement DynamoDB helpers -- Provide `create_file_metadata` and `get_file_metadata` matching schema
- [x] `backend/main.py` -- Implement FastAPI app and `POST /files/upload` endpoint -- Wire together S3 upload and DynamoDB metadata persistence
- [x] `backend/tests/test_upload.py` -- Add automated tests for upload endpoint and utilities -- Verify happy paths, validation errors, and AWS mock operations

**Acceptance Criteria:**
- Given a valid multipart file and recipient email list sent to `POST /files/upload`, when the endpoint is called, then a UUID `file_id` is created, the file is saved to S3 under `uploads/{file_id}/{original_filename}`, a DynamoDB record is created in `FileMetadata` with `accessed_by: []`, and HTTP 200 with upload details is returned.
- Given an invalid request (empty file or empty recipient list), when sent to `POST /files/upload`, then HTTP 400/422 validation error is returned.
- Given `pytest backend/tests`, when executed, then all upload and utility tests pass 100%.

## Design Notes

DynamoDB `FileMetadata` item structure:
```python
{
    "file_id": str(uuid.uuid4()),
    "s3_key": f"uploads/{file_id}/{original_filename}",
    "original_filename": file.filename,
    "uploader_email": uploader_email or "anonymous@cloudshare.local",
    "uploaded_at": datetime.now(timezone.utc).isoformat(),
    "content_type": file.content_type,
    "size_bytes": file_size,
    "recipients": recipients_list,
    "accessed_by": [],
    "recipient_tokens": {}
}
```

## Verification

**Commands:**
- `pytest backend/tests` -- expected: All tests pass with mocked AWS services.

## Suggested Review Order

**API Entry Point & Request Ingestion**

- FastAPI application and upload route handler parsing recipients and persisting metadata
  [`main.py:38`](../../backend/main.py#L38)

**Storage & Metadata Layer**

- S3 helper for private object uploads and presigned GET/PUT generation
  [`s3_utils.py:17`](../../backend/s3_utils.py#L17)

- DynamoDB item creation and idempotent access logging
  [`dynamo_utils.py:20`](../../backend/dynamo_utils.py#L20)

**Automated Tests & Dependencies**

- Unit test suite verifying S3 uploads, presigned URLs, and DynamoDB access logic
  [`test_unit.py:18`](../../backend/tests/test_unit.py#L18)

- Backend package dependencies for runtime and testing
  [`requirements.txt:1`](../../backend/requirements.txt#L1)
