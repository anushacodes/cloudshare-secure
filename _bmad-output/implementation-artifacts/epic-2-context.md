# Epic 2 Context: Automated Lifecycle & Completion-Based Deletion

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Automatically monitor file access state across recipients and purge files from S3 and DynamoDB as soon as all designated recipients have accessed their link, or upon reaching the 30-day fallback expiry threshold.

## Stories

- Story 2.1: Standalone Lifecycle Auto-Deletion Lambda Function
- Story 2.2: Amazon EventBridge Scheduled Rule & IAM Scoping

## Requirements & Constraints

- Auto-deletion engine must run as an independent, serverless AWS Lambda function decoupled from the FastAPI backend.
- Deletion condition: `set(recipients) == set(accessed_by)` OR `uploaded_at` older than 30 days.
- Deletes both the S3 storage object and the DynamoDB `FileMetadata` record.
- Structured logging with clear deletion metrics.

## Technical Decisions

- **Runtime:** Python 3.10+ standalone AWS Lambda handler (`lambda_handler(event, context)`).
- **Environment Variables:** `DYNAMODB_TABLE_NAME` (default `FileMetadata`), `S3_BUCKET_NAME` (default `cloudshare-secure-bucket`), `HARD_EXPIRY_DAYS` (default `30`).
- **AWS Clients:** Boto3 `s3` and `dynamodb`.
