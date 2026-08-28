# Architecture Diagrams

## System Overview

```
┌─────────────┐        ┌──────────────┐        ┌──────────────┐
│ React (TS)  │──REST──▶  FastAPI      │──boto3──▶  AWS S3      │
│ frontend    │◀───────│  backend      │◀────────│  (file store)│
└─────────────┘        └──────┬───────┘        └──────────────┘
                                │
                                ├──────────────▶ DynamoDB
                                │                (FileMetadata table)
                                │
                                └──────────────▶ AWS SES
                                                 (recipient emails)

                        ┌──────────────┐
                        │ EventBridge  │  (scheduled trigger, e.g. every 15 min)
                        │  schedule    │
                        └──────┬───────┘
                                ▼
                        ┌──────────────┐
                        │ Lambda       │  scans DynamoDB, compares
                        │ (deletion)   │  recipients vs accessed_by,
                        └──────┬───────┘  deletes from S3 + DynamoDB
                                ▼
                        ┌──────────────┐
                        │ S3 + DynamoDB│
                        └──────────────┘
```

## Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Uploader
    actor Recipient
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant S3 as AWS S3
    participant DB as DynamoDB
    participant SES as AWS SES
    participant EB as EventBridge
    participant LM as Lambda

    Uploader->>FE: Select file & enter recipient emails
    FE->>BE: POST /files/upload
    BE->>S3: Put object (presigned PUT)
    BE->>DB: PutItem (file_id, recipients, accessed_by=[])
    BE->>SES: SendEmail with signed recipient link
    BE-->>FE: Upload confirmed

    Recipient->>BE: GET /files/{file_id}/access?token=...
    BE->>DB: Validate token & append to accessed_by
    BE->>S3: Generate presigned GET URL
    BE-->>Recipient: Presigned S3 Download URL
    Recipient->>S3: Download file directly

    EB->>LM: Trigger scheduled check (e.g. every 15 min)
    LM->>DB: Scan FileMetadata
    Note over LM: Check: set(recipients) == set(accessed_by)
    LM->>S3: DeleteObject
    LM->>DB: DeleteItem
```
