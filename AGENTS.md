<!-- bmad:context -->
<!-- Verified 2026-08-28 against e89c8c5. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## cloudshare-secure

Serverless cloud file sharing platform with completion-based auto-deletion. React/TypeScript frontend (`frontend/`), FastAPI backend (`backend/`), and standalone deletion Lambda (`lambda/`). Specs live in `_bmad-output/specs/spec-cloudshare-secure/`, architectural guides in `docs/`.

## Policy

- Never commit `.env` or hardcode AWS credentials; local development loads credentials from gitignored environment variables.
- S3 bucket must have all direct public access blocked; all file transfers use short-lived presigned URLs.
- The React frontend must never talk to AWS directly or hold AWS credentials; all AWS operations route through the backend or Lambda.

## Where things are

- Backend API & route handlers: `backend/main.py`
- S3 presigned URL helpers: `backend/s3_utils.py`
- DynamoDB access & metadata operations: `backend/dynamo_utils.py`
- SES email dispatch: `backend/ses_utils.py`
- Lifecycle auto-deletion Lambda: `lambda/lambda_function.py`
- Frontend UI components: `frontend/src/components/`

## Running and verifying

- Backend local run: `uvicorn main:app --reload` inside `backend/` (requires active virtual environment).
- Frontend local run: `npm run dev` inside `frontend/`.

## Conventions that differ from defaults

- File download links are cryptographically signed per-recipient (`/files/{file_id}/access?token=...`); do not track access by raw unverified email parameters.
- File storage keys are prefixed by UUID (`uploads/{file_id}/{original_filename}`), never by raw filename alone.
- DynamoDB access tracking is append-only into `accessed_by` list; check for existence before appending to avoid duplicate email entries.
- Lambda auto-deletion engine runs independently on an EventBridge schedule; do not invoke deletion logic synchronously within the upload API.

## Known pitfalls

- S3 presigned PUT URLs require matching `Content-Type` headers in client requests if specified during generation.
- DynamoDB reserved keywords (e.g. `status`, `date`) must use `ExpressionAttributeNames` in query/update expressions.

<!-- /bmad:context -->
