# Deferred Work

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Implement token expiration window / TTL validation in verify_recipient_token.
  evidence: Access tokens currently validate signatures and file IDs, but do not enforce a maximum age window before file deletion.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Use DynamoDB atomic list_append or set expressions with conditional checks for concurrent access tracking.
  evidence: Concurrent recipient download requests could race when updating accessed_by list in DynamoDB.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Configure environment-specific CORS allowed origins instead of wildcard in backend/main.py.
  evidence: Wildcard origins with allow_credentials=True is rejected by browsers and should use explicit origins for production.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Add streaming upload support and max file size limits in FastAPI upload route.
  evidence: Loading entire file into memory via await file.read() could cause high memory usage on very large file uploads.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Add email format validation for recipient addresses prior to token generation.
  evidence: Validating email syntax prevents generating tokens for malformed addresses.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Add filename sanitization and path traversal guards in S3 key generation.
  evidence: Sanitizing original_filename with os.path.basename ensures S3 keys cannot contain unintended relative path components.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Implement S3 object cleanup/rollback if DynamoDB metadata persistence fails during upload.
  evidence: If DynamoDB fails after S3 put_object, the uploaded file remains orphaned in S3.

- source_spec: `_bmad-output/implementation-artifacts/spec-refactor-python-engineering-standards.md`
  summary: Enforce default server-side encryption (AES256/KMS) on S3 upload helpers.
  evidence: Specifying ServerSideEncryption on put_object ensures at-rest encryption compliance.
