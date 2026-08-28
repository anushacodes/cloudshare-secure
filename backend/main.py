import os
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from s3_utils import upload_file_to_s3
from dynamo_utils import create_file_metadata, get_file_metadata
from auth import generate_recipient_token, verify_recipient_token
from ses_utils import send_recipient_email

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="CloudShare Secure API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UploadResponse(BaseModel):
    file_id: str
    original_filename: str
    size_bytes: int
    content_type: str
    uploaded_at: str
    recipients: List[str]
    s3_key: str
    recipient_links: Dict[str, str]

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/files/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    recipients: str = Form(...),
    uploader_email: Optional[str] = Form("anonymous@cloudshare.local")
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty"
        )

    # Parse recipients
    recipient_list: List[str] = []
    try:
        parsed = json.loads(recipients)
        if isinstance(parsed, list):
            recipient_list = [str(r).strip() for r in parsed if str(r).strip()]
        elif isinstance(parsed, str):
            recipient_list = [parsed.strip()]
    except Exception:
        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

    if not recipient_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one recipient email is required"
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    s3_key = f"uploads/{file_id}/{original_filename}"
    content_type = file.content_type or "application/octet-stream"
    uploaded_at = datetime.now(timezone.utc).isoformat()

    # Generate per-recipient signed access tokens
    recipient_tokens: Dict[str, str] = {}
    recipient_links: Dict[str, str] = {}
    base_app_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

    for email in recipient_list:
        token = generate_recipient_token(file_id=file_id, recipient_email=email)
        recipient_tokens[email] = token
        recipient_links[email] = f"{base_app_url}/files/{file_id}/access?token={token}"

    try:
        # Upload to S3
        upload_file_to_s3(file_bytes, s3_key, content_type)

        # Save metadata in DynamoDB with recipient_tokens mapping
        create_file_metadata(
            file_id=file_id,
            s3_key=s3_key,
            original_filename=original_filename,
            uploader_email=uploader_email or "anonymous@cloudshare.local",
            size_bytes=file_size,
            content_type=content_type,
            recipients=recipient_list,
            uploaded_at=uploaded_at,
            recipient_tokens=recipient_tokens
        )

        # Dispatch SES emails to recipients
        for email, link in recipient_links.items():
            send_recipient_email(
                recipient_email=email,
                original_filename=original_filename,
                access_url=link,
                uploader_email=uploader_email
            )

        return UploadResponse(
            file_id=file_id,
            original_filename=original_filename,
            size_bytes=file_size,
            content_type=content_type,
            uploaded_at=uploaded_at,
            recipients=recipient_list,
            s3_key=s3_key,
            recipient_links=recipient_links
        )
    except Exception as e:
        logger.exception("Upload processing error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
