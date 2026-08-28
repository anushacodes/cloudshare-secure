---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/specs/spec-cloudshare-secure/SPEC.md
  - _bmad-output/specs/spec-cloudshare-secure/stack.md
  - _bmad-output/specs/spec-cloudshare-secure/architecture-diagrams.md
  - docs/ARCHITECTURE.md
  - docs/STEPS.md
---

# cloudshare-secure - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for cloudshare-secure, decomposing the requirements from the Spec, Architecture, and implementation guides into implementable stories.

## Requirements Inventory

### Functional Requirements

- **FR1 (File Upload & Presigned Storage):** User can upload a file and specify a list of recipient email addresses. System generates a unique `file_id` (UUID), stores the file in S3 with key `uploads/{file_id}/{original_filename}`, and records metadata in DynamoDB (`file_id`, `s3_key`, `original_filename`, `uploader_email`, `uploaded_at`, `content_type`, `size_bytes`, `recipients`, `accessed_by: []`).
- **FR2 (Cryptographic Token Generation & SES Email Dispatch):** System generates a cryptographically signed access token per recipient and dispatches a personalized email via AWS SES containing the access link (`/files/{file_id}/access?token=...`).
- **FR3 (Recipient Token Access & Download):** Recipient opens their access link; system validates the signed token, atomically appends the recipient's email to `accessed_by` in DynamoDB if not previously present, and returns a short-lived presigned S3 GET URL for direct file download.
- **FR4 (Automated Completion-Based Deletion):** Standalone scheduled Lambda (triggered via EventBridge every 10–15 min) scans DynamoDB `FileMetadata`, checks if `set(recipients) == set(accessed_by)`, and if matched, deletes the S3 object and deletes the DynamoDB record.
- **FR5 (Fallback Hard Expiry Deletion):** Scheduled Lambda detects files older than 30 days regardless of access status and automatically purges the S3 object and DynamoDB record.
- **FR6 (Uploader Authentication & Active Files Dashboard):** Uploader authenticates (JWT bearer token) and views an active dashboard of uploaded files, showing filename, upload date, size, and per-recipient access breakdown (accessed vs pending).
- **FR7 (Manual Revocation / Early File Deletion):** Authenticated uploader can manually trigger immediate deletion of an uploaded file via `DELETE /files/{file_id}`, deleting the S3 object and DynamoDB record before all recipients have accessed.

### NonFunctional Requirements

- **NFR1 (Zero Public S3 Access):** S3 bucket must block all direct public access; all upload/download operations use temporary presigned URLs.
- **NFR2 (Access Link Integrity & Non-Repudiation):** Download links must be cryptographically signed per recipient to prevent unverified email parameter tampering or link forwarding fraud.
- **NFR3 (Architectural Decoupling & Serverless Execution):** The auto-deletion engine runs as an isolated, independent Lambda triggered by EventBridge; the FastAPI backend never executes batch deletion logic.
- **NFR4 (Credential Security & Least Privilege):** React frontend must never hold AWS credentials or connect to AWS services directly; backend and Lambda IAM roles must be strictly scoped to required S3, DynamoDB, and SES actions.
- **NFR5 (Data Store Idempotency & Safety):** Access tracking in DynamoDB must prevent duplicate entries in `accessed_by` and use `ExpressionAttributeNames` for DynamoDB reserved keywords.

### Additional Requirements

- **ARCH-1:** FastAPI backend running Python 3.10+ with `boto3`, `uvicorn`, `pydantic`.
- **ARCH-2:** React + TypeScript frontend scaffolded with Vite and modern responsive styling.
- **ARCH-3:** AWS S3 bucket with private ACL and CORS configuration for presigned PUT/GET.
- **ARCH-4:** DynamoDB table `FileMetadata` with partition key `file_id` (String).
- **ARCH-5:** AWS SES verified sender domain/identity and test sandbox recipient configuration.
- **ARCH-6:** Standalone Python AWS Lambda function triggered on an Amazon EventBridge schedule (15 min).

### UX Design Requirements

- **UX-DR1:** Upload form with dynamic row add/remove for recipient emails and progress feedback.
- **UX-DR2:** Recipient access/download landing page with clear download trigger and download state feedback.
- **UX-DR3:** Uploader management dashboard displaying active shares, per-recipient access status badges, and manual revoke action.

### FR Coverage Map

- **FR1:** Epic 1 (Story 1.1, Story 1.4) — File upload and presigned S3 storage
- **FR2:** Epic 1 (Story 1.2) — Cryptographic token generation & SES email dispatch
- **FR3:** Epic 1 (Story 1.3, Story 1.4) — Recipient token validation and direct download
- **FR4:** Epic 2 (Story 2.1, Story 2.2) — Automated completion-based deletion engine
- **FR5:** Epic 2 (Story 2.1) — Fallback 30-day hard expiry deletion
- **FR6:** Epic 3 (Story 3.1, Story 3.3) — Uploader authentication & access tracking dashboard
- **FR7:** Epic 3 (Story 3.2, Story 3.3) — Manual early revocation and immediate file purge

## Epic List

### Epic 1: Secure File Upload and Recipient Distribution
Enable users to upload files, generate cryptographic per-recipient access tokens, dispatch personalized email notifications via AWS SES, and allow recipients to download files securely via presigned S3 URLs.  
**FRs covered:** FR1, FR2, FR3 | **UX:** UX-DR1, UX-DR2

### Epic 2: Automated Lifecycle & Completion-Based Deletion
Automatically monitor file access state across recipients and purge files from S3 and DynamoDB as soon as all designated recipients have accessed their link, or upon reaching the 30-day fallback expiry threshold.  
**FRs covered:** FR4, FR5

### Epic 3: Uploader Dashboard and File Lifecycle Management
Allow authenticated uploaders to view an active dashboard of shared files, monitor real-time access status per recipient (accessed vs. pending), and manually revoke/delete files early.  
**FRs covered:** FR6, FR7 | **UX:** UX-DR3

---

## Epic 1: Secure File Upload and Recipient Distribution

Enable users to upload files, generate cryptographic per-recipient access tokens, dispatch personalized email notifications via AWS SES, and allow recipients to download files securely via presigned S3 URLs.

### Story 1.1: Backend Upload API with Presigned S3 Storage & DynamoDB Metadata

As a user,  
I want to upload a file to the backend API with a list of recipient emails,  
So that the file is stored securely in S3 and its access metadata is initialized in DynamoDB.

**Acceptance Criteria:**

**Given** a client sending a valid multipart file and a JSON list of recipient emails to `POST /files/upload`  
**When** the backend receives the request  
**Then** a unique UUID `file_id` is generated  
**And** the file is uploaded to the private S3 bucket under key `uploads/{file_id}/{original_filename}`  
**And** an item is created in DynamoDB `FileMetadata` with `file_id`, `s3_key`, `original_filename`, `uploader_email`, `uploaded_at` (ISO timestamp), `content_type`, `size_bytes`, `recipients`, and empty `accessed_by: []`  
**And** the endpoint returns HTTP `200 OK` containing `file_id`, `original_filename`, and upload confirmation.

### Story 1.2: Per-Recipient Cryptographic Token Generation & SES Email Notification

As a system,  
I want to generate a cryptographically signed access token per recipient and dispatch a notification email via AWS SES,  
So that each recipient receives their own unforgeable link to access the file.

**Acceptance Criteria:**

**Given** a newly uploaded file record in `FileMetadata`  
**When** recipient links are generated  
**Then** an HMAC-SHA256 signature is created for each recipient email and stored in `recipient_tokens`  
**And** AWS SES dispatches an email to each recipient address with a personalized link `/files/{file_id}/access?token={signed_token}`  
**And** if SES dispatch fails for an address, the error is logged without breaking the overall upload response.

### Story 1.3: Recipient Token Access & Presigned S3 Download Generation

As a recipient,  
I want to open my personalized access link without creating an account,  
So that I can download my shared file securely while the system logs my access.

**Acceptance Criteria:**

**Given** a recipient requesting `GET /files/{file_id}/access?token={token}`  
**When** the backend validates the cryptographic token against `FileMetadata`  
**Then** the recipient's email is atomically appended to `accessed_by` in DynamoDB if not already present  
**And** a short-lived presigned S3 GET URL (5-minute expiration) is generated  
**And** the client is redirected to the presigned S3 download URL (or returns the download URL in JSON)  
**And** an invalid or tampered token returns HTTP `403 Forbidden`.

### Story 1.4: Frontend Upload & Recipient Access User Interface

As a user or recipient,  
I want an intuitive web interface for uploading files with dynamic recipient fields and downloading shared files,  
So that I can interact with the file sharing platform from a browser.

**Acceptance Criteria:**

**Given** a user on the React upload view  
**When** they select a file and dynamically add or remove recipient email fields  
**Then** the UI validates email inputs and displays upload progress feedback during `POST /files/upload`  
**And Given** a recipient opening an access link in their browser  
**When** the access page loads  
**Then** it initiates download through `GET /files/{file_id}/access?token=...` and provides clear visual feedback on download status.

---

## Epic 2: Automated Lifecycle & Completion-Based Deletion

Automatically monitor file access state across recipients and purge files from S3 and DynamoDB as soon as all designated recipients have accessed their link, or upon reaching the 30-day fallback expiry threshold.

### Story 2.1: Standalone Lifecycle Auto-Deletion Lambda Function

As a system administrator,  
I want a serverless Lambda function to scan DynamoDB and delete files that meet deletion conditions,  
So that completed or expired files are automatically cleaned up from storage and database.

**Acceptance Criteria:**

**Given** the deletion Lambda handler is triggered  
**When** it scans the `FileMetadata` DynamoDB table  
**Then** for every record where `set(recipients) == set(accessed_by)` OR `uploaded_at` is older than 30 days  
**And** it deletes the object from S3 using `s3_key`  
**And** it deletes the item from DynamoDB `FileMetadata`  
**And** it logs detailed deletion metrics (file ID, reason for deletion, total purged).

### Story 2.2: Amazon EventBridge Scheduled Rule & IAM Scoping

As a DevOps engineer,  
I want an EventBridge schedule rule to trigger the deletion Lambda periodically under a least-privilege IAM role,  
So that automated cleanup executes continuously without manual intervention or over-privileged access.

**Acceptance Criteria:**

**Given** the Lambda function deployed to AWS  
**When** an EventBridge recurring rule (e.g. rate 15 minutes) is configured  
**Then** EventBridge reliably invokes the Lambda on schedule  
**And** the Lambda execution IAM role allows only `s3:DeleteObject` on the specific bucket and `dynamodb:Scan`, `dynamodb:DeleteItem` on `FileMetadata`.

---

## Epic 3: Uploader Dashboard and File Lifecycle Management

Allow authenticated uploaders to view an active dashboard of shared files, monitor real-time access status per recipient (accessed vs. pending), and manually revoke/delete files early.

### Story 3.1: Uploader Authentication & File Status Listing API

As an uploader,  
I want to authenticate with JWT and query my uploaded files,  
So that I can see the real-time access status of every recipient I shared a file with.

**Acceptance Criteria:**

**Given** an authenticated uploader calling `GET /files` with a valid JWT bearer token  
**When** the backend receives the request  
**Then** it queries DynamoDB `FileMetadata` for all items where `uploader_email` matches the token  
**And** returns a list of active files with filename, upload timestamp, size, recipients list, and `accessed_by` list  
**And** unauthenticated requests return HTTP `401 Unauthorized`.

### Story 3.2: Manual File Revocation & Early Deletion API

As an uploader,  
I want to manually delete an uploaded file before all recipients have accessed it,  
So that I can immediately revoke access to sensitive files if needed.

**Acceptance Criteria:**

**Given** an authenticated uploader calling `DELETE /files/{file_id}`  
**When** the backend validates that `uploader_email` matches the file record owner  
**Then** it deletes the file object from S3  
**And** it deletes the record from DynamoDB `FileMetadata`  
**And** returns HTTP `200 OK` confirming manual revocation.

### Story 3.3: Uploader Management Dashboard UI

As an uploader,  
I want a web dashboard displaying all my active files with per-recipient access badges and a manual delete button,  
So that I can monitor and manage my shared files visually.

**Acceptance Criteria:**

**Given** an authenticated user on the React dashboard  
**When** the dashboard loads  
**Then** it displays all active uploaded files with metadata and color-coded badges for each recipient (`Accessed` vs `Pending`)  
**And** clicking "Revoke / Delete" triggers a confirmation prompt followed by `DELETE /files/{file_id}`, removing the file from the list.
