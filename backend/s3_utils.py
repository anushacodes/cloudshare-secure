"""S3 storage utility operations for uploads, deletions, and presigned URLs."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import get_settings


def get_s3_client() -> Any:
    """Instantiate and return a boto3 S3 client."""
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
    )


def get_s3_bucket_name() -> str:
    """Retrieve the configured S3 bucket name."""
    return get_settings().S3_BUCKET_NAME


def upload_file_to_s3(
    file_bytes: bytes,
    s3_key: str,
    content_type: str = "application/octet-stream",
) -> bool:
    """Upload raw bytes to S3."""
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    try:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        return True
    except ClientError as e:
        raise e


def generate_presigned_get_url(s3_key: str, expires_in: int = 300) -> str:
    """Generate a presigned GET URL for downloading an S3 object."""
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )


def generate_presigned_put_url(
    s3_key: str,
    content_type: str = "application/octet-stream",
    expires_in: int = 300,
) -> str:
    """Generate a presigned PUT URL for uploading an S3 object."""
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": s3_key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def delete_file_from_s3(s3_key: str) -> bool:
    """Delete an object from S3."""
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    try:
        s3.delete_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        raise e

