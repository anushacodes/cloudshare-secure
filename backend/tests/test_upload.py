import os
import json
import pytest
from moto import mock_aws
import boto3
from fastapi.testclient import TestClient

# Set mock env vars
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["DYNAMODB_TABLE_NAME"] = "FileMetadata"

from main import app
from s3_utils import get_s3_client, upload_file_to_s3, generate_presigned_get_url, generate_presigned_put_url
from dynamo_utils import get_dynamo_resource, create_file_metadata, get_file_metadata, add_recipient_access

@pytest.fixture
def aws_setup():
    with mock_aws():
        # Setup S3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        # Setup DynamoDB
        dynamo = boto3.resource("dynamodb", region_name="us-east-1")
        dynamo.create_table(
            TableName="FileMetadata",
            KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "file_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        yield

def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_s3_utils(aws_setup):
    s3_key = "uploads/123/sample.txt"
    content = b"Hello CloudShare"
    assert upload_file_to_s3(content, s3_key, "text/plain") is True

    get_url = generate_presigned_get_url(s3_key)
    assert "https://test-bucket.s3.amazonaws.com/uploads/123/sample.txt" in get_url

    put_url = generate_presigned_put_url(s3_key, "text/plain")
    assert "https://test-bucket.s3.amazonaws.com/uploads/123/sample.txt" in put_url

def test_dynamo_utils(aws_setup):
    item = create_file_metadata(
        file_id="fid-123",
        s3_key="uploads/fid-123/doc.pdf",
        original_filename="doc.pdf",
        uploader_email="user@test.com",
        size_bytes=1024,
        content_type="application/pdf",
        recipients=["a@test.com", "b@test.com"],
        uploaded_at="2026-08-28T00:00:00Z"
    )
    assert item["file_id"] == "fid-123"

    fetched = get_file_metadata("fid-123")
    assert fetched is not None
    assert fetched["original_filename"] == "doc.pdf"
    assert fetched["accessed_by"] == []

    updated = add_recipient_access("fid-123", "a@test.com")
    assert updated["accessed_by"] == ["a@test.com"]

    # Idempotent access
    updated_again = add_recipient_access("fid-123", "a@test.com")
    assert updated_again["accessed_by"] == ["a@test.com"]

def test_upload_endpoint_happy_path(aws_setup):
    client = TestClient(app)
    files = {"file": ("test.txt", b"Test file content", "text/plain")}
    data = {
        "recipients": json.dumps(["alice@example.com", "bob@example.com"]),
        "uploader_email": "uploader@example.com"
    }
    response = client.post("/files/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["original_filename"] == "test.txt"
    assert res_data["size_bytes"] == len(b"Test file content")
    assert res_data["recipients"] == ["alice@example.com", "bob@example.com"]
    assert res_data["s3_key"].startswith("uploads/")

    # Verify item in DynamoDB
    meta = get_file_metadata(res_data["file_id"])
    assert meta is not None
    assert meta["uploader_email"] == "uploader@example.com"
    assert meta["accessed_by"] == []

def test_upload_endpoint_empty_recipients(aws_setup):
    client = TestClient(app)
    files = {"file": ("test.txt", b"Test content", "text/plain")}
    data = {"recipients": json.dumps([])}
    response = client.post("/files/upload", files=files, data=data)
    assert response.status_code == 400
    assert "At least one recipient email is required" in response.json()["detail"]
