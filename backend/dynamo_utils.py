import os
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional, Any

def get_dynamo_resource():
    return boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )

def get_file_table():
    table_name = os.getenv("DYNAMODB_TABLE_NAME", "FileMetadata")
    dynamo = get_dynamo_resource()
    return dynamo.Table(table_name)

def create_file_metadata(
    file_id: str,
    s3_key: str,
    original_filename: str,
    uploader_email: str,
    size_bytes: int,
    content_type: str,
    recipients: List[str],
    uploaded_at: str,
    recipient_tokens: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    table = get_file_table()
    item = {
        "file_id": file_id,
        "s3_key": s3_key,
        "original_filename": original_filename,
        "uploader_email": uploader_email,
        "uploaded_at": uploaded_at,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "recipients": recipients,
        "accessed_by": [],
        "recipient_tokens": recipient_tokens or {}
    }
    try:
        table.put_item(Item=item)
        return item
    except ClientError as e:
        raise e

def get_file_metadata(file_id: str) -> Optional[Dict[str, Any]]:
    table = get_file_table()
    try:
        response = table.get_item(Key={"file_id": file_id})
        return response.get("Item")
    except ClientError as e:
        raise e

def add_recipient_access(file_id: str, recipient_email: str) -> Optional[Dict[str, Any]]:
    table = get_file_table()
    item = get_file_metadata(file_id)
    if not item:
        return None
    accessed_by = item.get("accessed_by", [])
    if recipient_email not in accessed_by:
        accessed_by.append(recipient_email)
        table.update_item(
            Key={"file_id": file_id},
            UpdateExpression="SET accessed_by = :accessed",
            ExpressionAttributeValues={":accessed": accessed_by}
        )
        item["accessed_by"] = accessed_by
    return item

def delete_file_metadata(file_id: str) -> bool:
    table = get_file_table()
    try:
        table.delete_item(Key={"file_id": file_id})
        return True
    except ClientError as e:
        raise e
