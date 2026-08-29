"""Amazon SES email notification dispatch utilities."""

from __future__ import annotations

import html
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import get_settings

logger = logging.getLogger(__name__)


def get_ses_client() -> Any:
    """Instantiate and return a boto3 SES client."""
    settings = get_settings()
    return boto3.client(
        "ses",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
    )


def get_sender_email() -> str:
    """Retrieve the configured SES sender email address."""
    return get_settings().SES_SENDER_EMAIL


def send_recipient_email(
    recipient_email: str,
    original_filename: str,
    access_url: str,
    uploader_email: str | None = None,
) -> bool:
    """Dispatch an email with signed access link to a recipient."""
    ses = get_ses_client()
    sender = get_sender_email()
    uploader_display = uploader_email or "Someone"

    escaped_uploader = html.escape(uploader_display)
    escaped_filename = html.escape(original_filename)
    escaped_url = html.escape(access_url)

    subject = f"File shared with you: {original_filename}"
    text_body = f"""Hello,

{uploader_display} has shared a file with you on CloudShare Secure:

File: {original_filename}
Download link: {access_url}

Please note: Once all recipients access their links, this file will be automatically deleted from cloud storage.

Best regards,
CloudShare Secure Team"""

    html_body = f"""<html>
<head></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <h2 style="color: #2563eb;">CloudShare Secure</h2>
    <p>Hello,</p>
    <p><strong>{escaped_uploader}</strong> has shared a file with you:</p>
    <div style="background-color: #f8fafc; padding: 12px; border-radius: 6px; margin: 16px 0;">
      <p style="margin: 0; font-size: 16px;"><strong>📄 {escaped_filename}</strong></p>
    </div>
    <p>Click the button below to download your file:</p>
    <p style="margin: 24px 0;">
      <a href="{escaped_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Download File</a>
    </p>
    <p style="font-size: 13px; color: #64748b;">Or copy this URL into your browser:<br/><a href="{escaped_url}">{escaped_url}</a></p>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
    <p style="font-size: 12px; color: #94a3b8;">
      ⚡ <em>Automated Lifecycle: Once all recipients download their copy, this file will be automatically purged from storage.</em>
    </p>
  </div>
</body>
</html>"""

    try:
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return True
    except ClientError as e:
        logger.warning(f"Failed to send email to {recipient_email}: {e}")
        return False

