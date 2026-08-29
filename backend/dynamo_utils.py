"""DynamoDB metadata persistence operations for files and recipient access."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import get_settings


def get_dynamo_resource() -> Any:
    """Instantiate and return a boto3 DynamoDB resource."""
    settings = get_settings()
    return boto3.resource(
        "dynamodb",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
    )


def get_file_table() -> Any:
    """Retrieve the DynamoDB Table instance for file metadata."""
    table_name = get_settings().DYNAMODB_TABLE_NAME
    dynamo = get_dynamo_resource()
    return dynamo.Table(table_name)


def create_file_metadata(
    file_id: str,
    s3_key: str,
    original_filename: str,
    uploader_email: str,
    size_bytes: int,
    content_type: str,
    recipients: list[str],
    uploaded_at: str,
    recipient_tokens: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Store newly uploaded file metadata record in DynamoDB."""
    table = get_file_table()
    item: dict[str, Any] = {
        "file_id": file_id,
        "s3_key": s3_key,
        "original_filename": original_filename,
        "uploader_email": uploader_email,
        "uploaded_at": uploaded_at,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "recipients": recipients,
        "accessed_by": [],
        "recipient_tokens": recipient_tokens or {},
    }
    try:
        table.put_item(Item=item)
        return item
    except ClientError as e:
        raise e


def get_file_metadata(file_id: str) -> dict[str, Any] | None:
    """Fetch metadata for a given file_id from DynamoDB."""
    table = get_file_table()
    try:
        response = table.get_item(Key={"file_id": file_id})
        return response.get("Item")
    except ClientError as e:
        raise e


def add_recipient_access(
    file_id: str, recipient_email: str
) -> dict[str, Any] | None:
    """Idempotently append a recipient email to the accessed_by list."""
    table = get_file_table()
    item = get_file_metadata(file_id)
    if not item:
        return None

    accessed_by: list[str] = item.get("accessed_by") or []
    if recipient_email not in accessed_by:
        accessed_by.append(recipient_email)
        table.update_item(
            Key={"file_id": file_id},
            UpdateExpression="SET accessed_by = :accessed",
            ExpressionAttributeValues={":accessed": accessed_by},
        )
        item["accessed_by"] = accessed_by
    return item


def delete_file_metadata(file_id: str) -> bool:
    """Delete a file metadata record from DynamoDB."""
    table = get_file_table()
    try:
        table.delete_item(Key={"file_id": file_id})
        return True
    except ClientError as e:
        raise e

