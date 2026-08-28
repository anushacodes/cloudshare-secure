# Technical Stack & Specifications

## Tech Stack

| Component | Technology / Service | Role |
|---|---|---|
| Frontend | React, TypeScript, Vite | Uploader UI, recipient access handling, file status dashboard |
| Backend | Python 3.10+, FastAPI, Boto3, Uvicorn | REST API, auth, presigned URL generation, DynamoDB & SES integration |
| Storage | AWS S3 | Private file storage with UUID key paths |
| Database | AWS DynamoDB | `FileMetadata` table for tracking recipient access state |
| Email Service | AWS SES | Dispatching per-recipient signed access links |
| Automation | AWS Lambda, Amazon EventBridge | Scheduled cron-driven lifecycle evaluation and auto-deletion |

## Data Model

**DynamoDB Table:** `FileMetadata`  
**Partition Key:** `file_id` (String - UUID v4)

| Attribute | Type | Description |
|---|---|---|
| `file_id` | String | Unique file identifier (UUID) |
| `s3_key` | String | Object path in S3 (e.g. `uploads/{file_id}/{filename}`) |
| `original_filename` | String | Original uploaded filename |
| `uploader_email` | String | Email of the uploader |
| `uploaded_at` | String | ISO 8601 timestamp of upload |
| `content_type` | String | MIME type |
| `size_bytes` | Number | File size in bytes |
| `recipients` | List[String] | Designated recipient email addresses |
| `accessed_by` | List[String] | Recipient email addresses that have accessed their download link |
| `recipient_tokens` | Map | Map of `recipient_email` -> `signed_token` |

## API Endpoints

- `POST /files/upload`: Upload file, save metadata, generate signed tokens, and dispatch SES emails.
- `GET /files/{file_id}/access?token=...`: Verify token, append recipient to `accessed_by`, return presigned GET URL.
- `GET /files`: (Authenticated) List uploader's active files with per-recipient access breakdown.
- `DELETE /files/{file_id}`: (Authenticated) Manual override to revoke/delete file early.
