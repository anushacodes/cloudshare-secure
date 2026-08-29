"""FastAPI application entry point and routes for CloudShare Secure."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from auth import generate_recipient_token, verify_recipient_token
from config import get_settings
from dynamo_utils import (
    add_recipient_access,
    create_file_metadata,
    get_file_metadata,
)
from s3_utils import generate_presigned_get_url, upload_file_to_s3
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
    """Response payload returned upon successful file upload."""

    file_id: str
    original_filename: str
    size_bytes: int
    content_type: str
    uploaded_at: str
    recipients: list[str]
    s3_key: str
    recipient_links: dict[str, str]


class AccessResponse(BaseModel):
    """Response payload returned upon successful recipient token verification."""

    file_id: str
    original_filename: str
    size_bytes: int
    content_type: str
    download_url: str
    recipient_email: str
    access_recorded: bool


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return health status and current UTC timestamp."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/files/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    recipients: str = Form(...),
    uploader_email: str | None = Form("anonymous@cloudshare.local"),
) -> UploadResponse:
    """Upload file, persist metadata, and dispatch recipient notification emails."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty",
        )

    # parse recipients list
    recipient_list: list[str] = []
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
            detail="At least one recipient email is required",
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    s3_key = f"uploads/{file_id}/{original_filename}"
    content_type = file.content_type or "application/octet-stream"
    uploaded_at = datetime.now(timezone.utc).isoformat()

    # generate per-recipient signed access tokens
    recipient_tokens: dict[str, str] = {}
    recipient_links: dict[str, str] = {}
    base_app_url = get_settings().APP_BASE_URL

    for email in recipient_list:
        token = generate_recipient_token(
            file_id=file_id, recipient_email=email
        )
        recipient_tokens[email] = token
        recipient_links[email] = (
            f"{base_app_url}/files/{file_id}/access?token={token}"
        )

    try:
        # upload to s3
        upload_file_to_s3(file_bytes, s3_key, content_type)

        # save metadata in dynamodb
        create_file_metadata(
            file_id=file_id,
            s3_key=s3_key,
            original_filename=original_filename,
            uploader_email=uploader_email or "anonymous@cloudshare.local",
            size_bytes=file_size,
            content_type=content_type,
            recipients=recipient_list,
            uploaded_at=uploaded_at,
            recipient_tokens=recipient_tokens,
        )

        # dispatch ses emails
        for email, link in recipient_links.items():
            send_recipient_email(
                recipient_email=email,
                original_filename=original_filename,
                access_url=link,
                uploader_email=uploader_email,
            )

        return UploadResponse(
            file_id=file_id,
            original_filename=original_filename,
            size_bytes=file_size,
            content_type=content_type,
            uploaded_at=uploaded_at,
            recipients=recipient_list,
            s3_key=s3_key,
            recipient_links=recipient_links,
        )
    except Exception as e:
        logger.exception("Upload processing error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@app.get("/files/{file_id}/access", response_model=AccessResponse)
async def access_file(
    file_id: str,
    token: str,
    redirect: bool = False,
) -> AccessResponse | RedirectResponse:
    """Validate recipient token, record access, and return or redirect to download url."""
    metadata = get_file_metadata(file_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or has already been deleted",
        )

    recipient_email = verify_recipient_token(token, file_id)
    if not recipient_email or recipient_email not in metadata.get(
        "recipients", []
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid, expired, or tampered access token",
        )

    add_recipient_access(file_id, recipient_email)

    s3_key = metadata.get("s3_key")
    if not s3_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File storage reference missing or invalid",
        )
    download_url = generate_presigned_get_url(s3_key, expires_in=300)

    if redirect:
        return RedirectResponse(
            url=download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    return AccessResponse(
        file_id=file_id,
        original_filename=metadata.get("original_filename", "downloaded_file"),
        size_bytes=int(metadata.get("size_bytes", 0)),
        content_type=metadata.get("content_type", "application/octet-stream"),
        download_url=download_url,
        recipient_email=recipient_email,
        access_recorded=True,
    )

