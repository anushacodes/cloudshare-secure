"""Integration tests for S3, DynamoDB, and file upload endpoints using Moto."""

from __future__ import annotations

import json
import os
from typing import Generator

import boto3
from fastapi.testclient import TestClient
from moto import mock_aws
import pytest

# configure test environment variables
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["DYNAMODB_TABLE_NAME"] = "FileMetadata"

from config import get_settings
from dynamo_utils import (
    add_recipient_access,
    create_file_metadata,
    get_file_metadata,
)
from main import app
from s3_utils import (
    generate_presigned_get_url,
    generate_presigned_put_url,
    upload_file_to_s3,
)

get_settings.cache_clear()


@pytest.fixture
def aws_setup() -> Generator[None, None, None]:
    """Provision mocked S3 bucket and DynamoDB table with Moto."""
    with mock_aws():
        # setup s3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        # setup dynamodb
        dynamo = boto3.resource("dynamodb", region_name="us-east-1")
        dynamo.create_table(
            TableName="FileMetadata",
            KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "file_id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


def test_health_check() -> None:
    """Verify /health endpoint returns 200 ok."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_s3_utils(aws_setup: None) -> None:
    """Verify S3 byte upload and presigned URL generation."""
    s3_key = "uploads/123/sample.txt"
    content = b"Hello CloudShare"
    assert upload_file_to_s3(content, s3_key, "text/plain") is True

    get_url = generate_presigned_get_url(s3_key)
    assert (
        "https://test-bucket.s3.amazonaws.com/uploads/123/sample.txt" in get_url
    )

    put_url = generate_presigned_put_url(s3_key, "text/plain")
    assert (
        "https://test-bucket.s3.amazonaws.com/uploads/123/sample.txt" in put_url
    )


def test_dynamo_utils(aws_setup: None) -> None:
    """Verify DynamoDB metadata creation, retrieval, and access recording."""
    item = create_file_metadata(
        file_id="fid-123",
        s3_key="uploads/fid-123/doc.pdf",
        original_filename="doc.pdf",
        uploader_email="user@test.com",
        size_bytes=1024,
        content_type="application/pdf",
        recipients=["a@test.com", "b@test.com"],
        uploaded_at="2026-08-28T00:00:00Z",
    )
    assert item["file_id"] == "fid-123"

    fetched = get_file_metadata("fid-123")
    assert fetched is not None
    assert fetched["original_filename"] == "doc.pdf"
    assert fetched["accessed_by"] == []

    updated = add_recipient_access("fid-123", "a@test.com")
    assert updated is not None
    assert updated["accessed_by"] == ["a@test.com"]

    # duplicate access should not add duplicate entry
    updated_again = add_recipient_access("fid-123", "a@test.com")
    assert updated_again is not None
    assert updated_again["accessed_by"] == ["a@test.com"]


def test_upload_endpoint_happy_path(aws_setup: None) -> None:
    """Verify file upload endpoint saves to S3 and DynamoDB."""
    client = TestClient(app)
    files = {"file": ("test.txt", b"Test file content", "text/plain")}
    data = {
        "recipients": json.dumps(["alice@example.com", "bob@example.com"]),
        "uploader_email": "uploader@example.com",
    }
    response = client.post("/files/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["original_filename"] == "test.txt"
    assert res_data["size_bytes"] == len(b"Test file content")
    assert res_data["recipients"] == ["alice@example.com", "bob@example.com"]
    assert res_data["s3_key"].startswith("uploads/")

    meta = get_file_metadata(res_data["file_id"])
    assert meta is not None
    assert meta["uploader_email"] == "uploader@example.com"
    assert meta["accessed_by"] == []


def test_upload_endpoint_empty_recipients(aws_setup: None) -> None:
    """Verify file upload with empty recipient list returns 400."""
    client = TestClient(app)
    files = {"file": ("test.txt", b"Test content", "text/plain")}
    data = {"recipients": json.dumps([])}
    response = client.post("/files/upload", files=files, data=data)
    assert response.status_code == 400
    assert "At least one recipient email is required" in response.json()["detail"]

