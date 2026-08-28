import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

# Mock boto3 and dotenv before importing utils
sys.modules["boto3"] = MagicMock()
sys.modules["dotenv"] = MagicMock()
botocore_exceptions = MagicMock()
class ClientError(Exception):
    pass
botocore_exceptions.ClientError = ClientError
sys.modules["botocore"] = MagicMock()
sys.modules["botocore.exceptions"] = botocore_exceptions

import s3_utils
import dynamo_utils
import auth
import ses_utils

class TestAuth(unittest.TestCase):
    def test_token_generation_and_verification(self):
        file_id = "test-fid-123"
        recipient = "alice@example.com"
        token = auth.generate_recipient_token(file_id, recipient)
        self.assertIsInstance(token, str)

        verified_email = auth.verify_recipient_token(token, file_id)
        self.assertEqual(verified_email, recipient)

    def test_token_verification_tampering(self):
        file_id = "test-fid-123"
        token = auth.generate_recipient_token(file_id, "alice@example.com")
        
        # Wrong file_id
        self.assertIsNone(auth.verify_recipient_token(token, "wrong-fid-456"))

        # Corrupted token
        corrupted = token[:-4] + "AAAA"
        self.assertIsNone(auth.verify_recipient_token(corrupted, file_id))

class TestSESUtils(unittest.TestCase):
    @patch("ses_utils.get_ses_client")
    def test_send_recipient_email_success(self, mock_get_ses):
        mock_ses = MagicMock()
        mock_get_ses.return_value = mock_ses

        sent = ses_utils.send_recipient_email(
            recipient_email="bob@example.com",
            original_filename="doc.pdf",
            access_url="http://localhost:8000/files/123/access?token=xyz",
            uploader_email="alice@example.com"
        )
        self.assertTrue(sent)
        mock_ses.send_email.assert_called_once()

class TestS3Utils(unittest.TestCase):
    @patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"})
    @patch("s3_utils.get_s3_client")
    def test_upload_file_to_s3(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        res = s3_utils.upload_file_to_s3(b"data", "uploads/123/file.txt", "text/plain")
        self.assertTrue(res)
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/123/file.txt",
            Body=b"data",
            ContentType="text/plain"
        )

    @patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"})
    @patch("s3_utils.get_s3_client")
    def test_generate_presigned_urls(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/file"
        mock_get_client.return_value = mock_client

        get_url = s3_utils.generate_presigned_get_url("uploads/123/file.txt")
        self.assertEqual(get_url, "https://s3.amazonaws.com/test-bucket/file")

class TestDynamoUtils(unittest.TestCase):
    @patch("dynamo_utils.get_file_table")
    def test_create_file_metadata(self, mock_get_table):
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        item = dynamo_utils.create_file_metadata(
            file_id="fid-123",
            s3_key="uploads/fid-123/file.txt",
            original_filename="file.txt",
            uploader_email="uploader@test.com",
            size_bytes=100,
            content_type="text/plain",
            recipients=["alice@test.com", "bob@test.com"],
            uploaded_at="2026-08-28T00:00:00Z"
        )
        self.assertEqual(item["file_id"], "fid-123")
        self.assertEqual(item["accessed_by"], [])
        mock_table.put_item.assert_called_once()

    @patch("dynamo_utils.get_file_table")
    def test_add_recipient_access_idempotent(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "file_id": "fid-123",
                "recipients": ["alice@test.com"],
                "accessed_by": []
            }
        }
        mock_get_table.return_value = mock_table

        updated = dynamo_utils.add_recipient_access("fid-123", "alice@test.com")
        self.assertEqual(updated["accessed_by"], ["alice@test.com"])
        mock_table.update_item.assert_called_once()

if __name__ == "__main__":
    unittest.main()
