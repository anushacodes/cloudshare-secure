# CloudShare Secure

A serverless cloud file sharing application built with AWS, FastAPI, and React. Files are uploaded and shared with designated recipients via per-recipient access links. Once all recipients have accessed their download link, a scheduled AWS Lambda function automatically purges the file from both Amazon S3 and DynamoDB.

---

## 🏗️ Architecture

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

### How It Works

1. **Upload & Distribute**: An uploader uploads a file and specifies recipient email addresses. The FastAPI backend uploads the file to S3, records metadata in DynamoDB, and dispatches unique signed download links via Amazon SES.
2. **Access & Logging**: When a recipient clicks their unique link, the backend validates the signed token, records the recipient's access in DynamoDB, and issues a short-lived presigned S3 download URL.
3. **Automated Lifecycle Deletion**: An Amazon EventBridge rule triggers an AWS Lambda function on a schedule (e.g., every 15 minutes). The Lambda scans DynamoDB, checks if `recipients == accessed_by`, and automatically deletes the file from S3 and cleans up the DynamoDB record.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React, TypeScript, Vite |
| **Backend** | Python, FastAPI, Boto3, Uvicorn |
| **Storage** | AWS S3 (Private buckets, presigned URLs) |
| **Database** | AWS DynamoDB (`FileMetadata` table) |
| **Email Service** | AWS SES |
| **Lifecycle Automation** | AWS Lambda, Amazon EventBridge |
| **Security** | UUID-based S3 keys, signed per-recipient access tokens |

---

## 📂 Project Structure

```
.
├── backend/
│   ├── main.py                # FastAPI app & route handlers
│   ├── auth.py                # Authentication & token verification
│   ├── dynamo_utils.py        # DynamoDB CRUD helpers
│   ├── s3_utils.py            # Presigned URL generation & S3 operations
│   ├── ses_utils.py           # SES email dispatch logic
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # React UI components (UploadForm, Dashboard, etc.)
│   │   ├── api/               # API client
│   │   └── App.tsx            # Main React application
│   └── package.json           # Frontend dependencies & scripts
├── lambda/
│   └── lambda_function.py     # Scheduled cleanup Lambda handler
└── docs/
    ├── ARCHITECTURE.md        # Detailed architecture & design doc
    └── STEPS.md               # Build checklist & implementation guide
```

---

## 🚀 Getting Started

### Prerequisites

- **AWS Account** with access to S3, DynamoDB, SES, Lambda, and EventBridge
- **Python 3.10+**
- **Node.js 18+** & npm
- **AWS CLI** configured locally

### AWS Resource Setup

1. **S3 Bucket**: Create a private S3 bucket with all public access blocked.
2. **DynamoDB**: Create a table named `FileMetadata` with partition key `file_id` (String).
3. **AWS SES**: Verify sender identity (and test recipient emails if operating in SES sandbox).
4. **AWS Lambda**: Deploy `lambda/lambda_function.py` with IAM permissions for S3 deletion and DynamoDB read/write.
5. **EventBridge**: Set up a recurring schedule (e.g., rate of 15 minutes) to trigger the Lambda function.

### Local Development

#### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start the development server
uvicorn main:app --reload
```

#### 2. Frontend Setup

```bash
cd frontend
npm install

# Start Vite dev server
npm run dev
```

---

## 🔒 Security Highlights

- **Zero Direct S3 Public Access**: All file downloads use short-lived presigned S3 URLs generated on-demand.
- **Signed Recipient Tokens**: Per-recipient tokens prevent unauthorized link sharing or falsified access confirmations.
- **UUID Namespacing**: S3 storage keys are UUID-isolated to prevent key guessing and path enumeration.
- **Least-Privilege IAM**: Backend and Lambda roles are isolated and strictly scoped to required S3/DynamoDB actions.