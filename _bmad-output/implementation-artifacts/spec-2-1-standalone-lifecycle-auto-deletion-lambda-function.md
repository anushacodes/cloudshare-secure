---
title: "2.1 Standalone Lifecycle Auto-Deletion Lambda Function"
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

**Problem:** Files shared with recipients should not persist indefinitely once all recipients have retrieved them or after a reasonable lifespan.

**Approach:** Implement a standalone AWS Lambda function in `lambda/lambda_function.py` that scans the DynamoDB `FileMetadata` table, checks each item for full access completion (`set(recipients) == set(accessed_by)`) or 30-day hard expiry, deletes matching S3 objects and DynamoDB records, and logs execution metrics.

## Boundaries & Constraints

**Always:**
- Keep Lambda decoupled from FastAPI backend.
- Delete both S3 object (`s3_key`) and DynamoDB record (`file_id`) for every qualified item.
- Support 30-day fallback hard expiry (`HARD_EXPIRY_DAYS` configurable via env var).
- Include unit tests verifying all deletion triggers and non-deletion cases with mocked AWS services.

**Ask First:**
- Archiving metadata to cold storage instead of hard deleting from DynamoDB.

**Never:**
- Delete files that have pending unaccessed recipients unless they exceed the hard expiry threshold.
- Run batch deletion synchronously inside the FastAPI backend request cycle.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| All Recipients Accessed | Record with `recipients: [A, B]`, `accessed_by: [A, B]` | File deleted from S3 & DynamoDB | N/A |
| Pending Recipients (< 30 days) | `recipients: [A, B]`, `accessed_by: [A]` (uploaded 2 days ago) | Skipped / retained in S3 & DynamoDB | N/A |
| Hard Expiry (30+ days) | `recipients: [A, B]`, `accessed_by: [A]` (uploaded 35 days ago) | Purged from S3 & DynamoDB due to expiration | N/A |
| Empty Table | No records in `FileMetadata` | Clean execution, logs 0 deletions | N/A |
| S3 Object Missing / Already Deleted | DynamoDB record exists but S3 returns 404 on delete | Deletes DynamoDB record to prevent stuck state | Log warning and delete DynamoDB record |

</frozen-after-approval>

## Code Map

- `lambda/lambda_function.py` -- AWS Lambda handler function (`lambda_handler`) and deletion logic
- `lambda/test_lambda.py` -- Unit tests verifying deletion conditions and mock AWS interactions

## Tasks & Acceptance

**Execution:**
- [x] `lambda/lambda_function.py` -- Implement standalone Lambda lifecycle cleanup handler -- Evaluate access completion and hard expiry, perform S3 & DynamoDB deletions
- [x] `lambda/test_lambda.py` -- Add unit test suite for Lambda handler -- Test completion deletion, pending retention, hard expiry, and error handling

**Acceptance Criteria:**
- Given a file where all recipients have accessed the download link, when `lambda_handler` runs, then the S3 object and DynamoDB record are deleted.
- Given a file where some recipients have not accessed the link and upload is under 30 days old, when `lambda_handler` runs, then the file is retained.
- Given a file older than 30 days regardless of access count, when `lambda_handler` runs, then the file is purged.
- Given `python3 lambda/test_lambda.py`, when executed, then all test cases pass 100%.

## Verification

**Commands:**
- `python3 lambda/test_lambda.py` -- expected: All Lambda unit tests pass.

## Suggested Review Order

**Lambda Lifecycle Handler**

- Standalone entry point evaluating access conditions and purging S3 objects + DynamoDB records
  [`lambda_function.py:34`](../../lambda/lambda_function.py#L34)

**Evaluation Condition Logic**

- Condition checking full recipient access completion vs. 30-day fallback expiry
  [`lambda_function.py:16`](../../lambda/lambda_function.py#L16)

**Automated Tests**

- Unit test suite verifying completion deletion, retention of pending items, and hard expiry
  [`test_lambda.py:18`](../../lambda/test_lambda.py#L18)
