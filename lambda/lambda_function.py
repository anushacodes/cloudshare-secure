import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_s3_client():
    return boto3.client("s3")

def get_dynamo_resource():
    return boto3.resource("dynamodb")

def should_delete(item: Dict[str, Any], expiry_days: int = 30) -> Tuple[bool, str]:
    recipients = set(item.get("recipients", []))
    accessed_by = set(item.get("accessed_by", []))

    # Condition 1: All recipients accessed
    if recipients and recipients.issubset(accessed_by):
        return True, "all_recipients_accessed"

    # Condition 2: Fallback hard expiry
    uploaded_at_str = item.get("uploaded_at")
    if uploaded_at_str:
        try:
            uploaded_at = datetime.fromisoformat(uploaded_at_str.replace("Z", "+00:00"))
            cutoff = datetime.now(timezone.utc) - timedelta(days=expiry_days)
            if uploaded_at < cutoff:
                return True, f"hard_expiry_exceeded_{expiry_days}_days"
        except Exception as e:
            logger.warning(f"Error parsing uploaded_at timestamp: {e}")

    return False, "retained"

def lambda_handler(event: Any = None, context: Any = None) -> Dict[str, Any]:
    bucket_name = os.getenv("S3_BUCKET_NAME", "cloudshare-secure-bucket")
    table_name = os.getenv("DYNAMODB_TABLE_NAME", "FileMetadata")
    expiry_days = int(os.getenv("HARD_EXPIRY_DAYS", "30"))

    s3 = get_s3_client()
    dynamo = get_dynamo_resource()
    table = dynamo.Table(table_name)

    logger.info(f"Starting lifecycle scan on table '{table_name}' against bucket '{bucket_name}'...")

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
                s3_key = item.get("s3_key")

                is_delete_ready, reason = should_delete(item, expiry_days)
                if not is_delete_ready:
                    continue

                logger.info(f"Purging file '{file_id}' (reason: {reason})...")

                # Delete from S3
                if s3_key:
                    try:
                        s3.delete_object(Bucket=bucket_name, Key=s3_key)
                        logger.info(f"Deleted S3 object: {s3_key}")
                    except Exception as e:
                        logger.warning(f"S3 deletion warning for '{s3_key}': {e}")

                # Delete from DynamoDB
                try:
                    table.delete_item(Key={"file_id": file_id})
                    logger.info(f"Deleted DynamoDB record: {file_id}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"DynamoDB deletion failed for '{file_id}': {e}")
                    errors_count += 1

            if "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items = response.get("Items", [])
            else:
                break

    except Exception as e:
        logger.exception(f"Lifecycle execution failed with error: {e}")
        return {
            "statusCode": 500,
            "error": str(e),
            "scanned": scanned_count,
            "deleted": deleted_count
        }

    summary = {
        "statusCode": 200,
        "scanned": scanned_count,
        "deleted": deleted_count,
        "errors": errors_count,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"Lifecycle scan complete: {summary}")
    return summary
