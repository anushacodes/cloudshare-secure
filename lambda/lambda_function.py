"""Lifecycle auto-deletion Lambda handler for CloudShare Secure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class LambdaSettings:
    """Runtime configuration for lifecycle auto-deletion Lambda."""

    S3_BUCKET_NAME: str
    DYNAMODB_TABLE_NAME: str
    HARD_EXPIRY_DAYS: int


@lru_cache
def get_settings() -> LambdaSettings:
    """Retrieve cached lambda configuration settings."""
    return LambdaSettings(
        S3_BUCKET_NAME=os.getenv("S3_BUCKET_NAME", "cloudshare-secure-bucket"),
        DYNAMODB_TABLE_NAME=os.getenv("DYNAMODB_TABLE_NAME", "FileMetadata"),
        HARD_EXPIRY_DAYS=int(os.getenv("HARD_EXPIRY_DAYS", "30")),
    )


def get_s3_client() -> Any:
    """Instantiate and return a boto3 S3 client."""
    return boto3.client("s3")


def get_dynamo_resource() -> Any:
    """Instantiate and return a boto3 DynamoDB resource."""
    return boto3.resource("dynamodb")


def should_delete(
    item: dict[str, Any],
    expiry_days: int = 30,
) -> tuple[bool, str]:
    """Determine whether a file item should be deleted based on lifecycle rules."""
    recipients = set(item.get("recipients", []))
    accessed_by = set(item.get("accessed_by", []))

    # condition 1: all recipients accessed
    if recipients and recipients.issubset(accessed_by):
        return True, "all_recipients_accessed"

    # condition 2: fallback hard expiry
    uploaded_at_str = item.get("uploaded_at")
    if uploaded_at_str:
        try:
            uploaded_at = datetime.fromisoformat(
                uploaded_at_str.replace("Z", "+00:00")
            )
            if uploaded_at.tzinfo is None:
                uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(days=expiry_days)
            if uploaded_at < cutoff:
                return True, f"hard_expiry_exceeded_{expiry_days}_days"
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Error parsing uploaded_at timestamp '{uploaded_at_str}': {e}"
            )

    return False, "retained"


def lambda_handler(
    event: dict[str, Any] | None = None,
    context: Any = None,
) -> dict[str, Any]:
    """Scan DynamoDB table, evaluate lifecycle rules, and purge eligible files."""
    settings = get_settings()
    bucket_name = settings.S3_BUCKET_NAME
    table_name = settings.DYNAMODB_TABLE_NAME
    expiry_days = settings.HARD_EXPIRY_DAYS

    s3 = get_s3_client()
    dynamo = get_dynamo_resource()
    table = dynamo.Table(table_name)

    logger.info(
        f"Starting lifecycle scan on table '{table_name}' against bucket '{bucket_name}'..."
    )

    scanned_count = 0
    deleted_count = 0
    errors_count = 0

    try:
        response = table.scan()
        items = response.get("Items", [])

        while True:
            for item in items:
                scanned_count += 1
                file_id = item.get("file_id")
                if not file_id:
                    logger.warning(
                        "Item missing file_id partition key; skipping"
                    )
                    continue
                s3_key = item.get("s3_key")

                is_delete_ready, reason = should_delete(item, expiry_days)
                if not is_delete_ready:
                    continue

                logger.info(f"Purging file '{file_id}' (reason: {reason})...")

                # delete from s3
                if s3_key:
                    try:
                        s3.delete_object(Bucket=bucket_name, Key=s3_key)
                        logger.info(f"Deleted S3 object: {s3_key}")
                    except ClientError as e:
                        logger.warning(
                            f"S3 deletion warning for '{s3_key}': {e}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Unexpected S3 deletion error for '{s3_key}': {e}"
                        )

                # delete from dynamodb
                try:
                    table.delete_item(Key={"file_id": file_id})
                    logger.info(f"Deleted DynamoDB record: {file_id}")
                    deleted_count += 1
                except ClientError as e:
                    logger.error(
                        f"DynamoDB deletion failed for '{file_id}': {e}"
                    )
                    errors_count += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected DynamoDB deletion error for '{file_id}': {e}"
                    )
                    errors_count += 1

            if "LastEvaluatedKey" in response:
                response = table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items = response.get("Items", [])
            else:
                break

    except Exception as e:
        logger.exception(f"Lifecycle execution failed with error: {e}")
        return {
            "statusCode": 500,
            "error": str(e),
            "scanned": scanned_count,
            "deleted": deleted_count,
        }

    summary = {
        "statusCode": 200,
        "scanned": scanned_count,
        "deleted": deleted_count,
        "errors": errors_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Lifecycle scan complete: {summary}")
    return summary

