import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional

def get_s3_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )

def get_s3_bucket_name() -> str:
    return os.getenv("S3_BUCKET_NAME", "cloudshare-secure-bucket")

def upload_file_to_s3(file_bytes: bytes, s3_key: str, content_type: str = "application/octet-stream") -> bool:
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    try:
        s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type
        )
        return True
    except ClientError as e:
        raise e

def generate_presigned_get_url(s3_key: str, expires_in: int = 300) -> str:
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expires_in
    )

def generate_presigned_put_url(s3_key: str, content_type: str = "application/octet-stream", expires_in: int = 300) -> str:
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": s3_key, "ContentType": content_type},
        ExpiresIn=expires_in
    )

def delete_file_from_s3(s3_key: str) -> bool:
    s3 = get_s3_client()
    bucket = get_s3_bucket_name()
    try:
        s3.delete_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        raise e
