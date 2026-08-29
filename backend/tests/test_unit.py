"""Unit tests for backend modules: auth, SES, S3, DynamoDB, and access endpoints."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

import auth
from config import get_settings
import dynamo_utils
import main
import s3_utils
import ses_utils


class TestAuth(unittest.TestCase):
    """Unit tests for HMAC token generation and verification."""

    def test_token_generation_and_verification(self) -> None:
        file_id = "test-fid-123"
        recipient = "alice@example.com"
        token = auth.generate_recipient_token(file_id, recipient)
        self.assertIsInstance(token, str)

        verified_email = auth.verify_recipient_token(token, file_id)
        self.assertEqual(verified_email, recipient)

    def test_token_verification_tampering(self) -> None:
        file_id = "test-fid-123"
        token = auth.generate_recipient_token(file_id, "alice@example.com")

        # wrong file_id
        self.assertIsNone(auth.verify_recipient_token(token, "wrong-fid-456"))

        # corrupted token
        corrupted = token[:-4] + "AAAA"
        self.assertIsNone(auth.verify_recipient_token(corrupted, file_id))


class TestSESUtils(unittest.TestCase):
    """Unit tests for SES email dispatch utility."""

    @patch("ses_utils.get_ses_client")
    def test_send_recipient_email_success(self, mock_get_ses: MagicMock) -> None:
        mock_ses = MagicMock()
        mock_get_ses.return_value = mock_ses

        sent = ses_utils.send_recipient_email(
            recipient_email="bob@example.com",
            original_filename="doc.pdf",
            access_url="http://localhost:8000/files/123/access?token=xyz",
            uploader_email="alice@example.com",
        )
        self.assertTrue(sent)
        mock_ses.send_email.assert_called_once()


class TestS3Utils(unittest.TestCase):
    """Unit tests for S3 storage operations and presigned URL generators."""

    @patch("s3_utils.get_s3_bucket_name", return_value="test-bucket")
    @patch("s3_utils.get_s3_client")
    def test_upload_file_to_s3(
        self, mock_get_client: MagicMock, mock_get_bucket: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        res = s3_utils.upload_file_to_s3(
            b"data", "uploads/123/file.txt", "text/plain"
        )
        self.assertTrue(res)
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/123/file.txt",
            Body=b"data",
            ContentType="text/plain",
        )

    @patch("s3_utils.get_s3_bucket_name", return_value="test-bucket")
    @patch("s3_utils.get_s3_client")
    def test_generate_presigned_urls(
        self, mock_get_client: MagicMock, mock_get_bucket: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/file"
        )
        mock_get_client.return_value = mock_client

        get_url = s3_utils.generate_presigned_get_url("uploads/123/file.txt")
        self.assertEqual(get_url, "https://s3.amazonaws.com/test-bucket/file")

    @patch("s3_utils.get_s3_bucket_name", return_value="test-bucket")
    @patch("s3_utils.get_s3_client")
    def test_delete_file_from_s3(
        self, mock_get_client: MagicMock, mock_get_bucket: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        res = s3_utils.delete_file_from_s3("uploads/123/file.txt")
        self.assertTrue(res)
        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/123/file.txt",
        )


class TestDynamoUtils(unittest.TestCase):
    """Unit tests for DynamoDB metadata CRUD operations."""

    @patch("dynamo_utils.get_file_table")
    def test_create_file_metadata(self, mock_get_table: MagicMock) -> None:
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
            uploaded_at="2026-08-28T00:00:00Z",
        )
        self.assertEqual(item["file_id"], "fid-123")
        self.assertEqual(item["accessed_by"], [])
        mock_table.put_item.assert_called_once()

    @patch("dynamo_utils.get_file_table")
    def test_add_recipient_access_idempotent(
        self, mock_get_table: MagicMock
    ) -> None:
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "file_id": "fid-123",
                "recipients": ["alice@test.com"],
                "accessed_by": [],
            }
        }
        mock_get_table.return_value = mock_table

        updated = dynamo_utils.add_recipient_access("fid-123", "alice@test.com")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["accessed_by"], ["alice@test.com"])
        mock_table.update_item.assert_called_once()

    @patch("dynamo_utils.get_file_table")
    def test_delete_file_metadata(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        res = dynamo_utils.delete_file_metadata("fid-123")
        self.assertTrue(res)
        mock_table.delete_item.assert_called_once_with(Key={"file_id": "fid-123"})


class TestAccessEndpoint(unittest.TestCase):
    """Unit tests for the /files/{file_id}/access FastAPI endpoint."""

    @patch("main.get_file_metadata")
    @patch("main.add_recipient_access")
    @patch("main.generate_presigned_get_url")
    def test_access_file_success(
        self,
        mock_get_url: MagicMock,
        mock_add_access: MagicMock,
        mock_get_meta: MagicMock,
    ) -> None:
        file_id = "fid-123"
        recipient = "alice@example.com"
        token = auth.generate_recipient_token(file_id, recipient)

        mock_get_meta.return_value = {
            "file_id": file_id,
            "original_filename": "presentation.pdf",
            "size_bytes": 2048,
            "content_type": "application/pdf",
            "s3_key": "uploads/fid-123/presentation.pdf",
            "recipients": [recipient],
            "accessed_by": [],
        }
        mock_get_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/uploads/fid-123/presentation.pdf"
        )

        res = asyncio.run(main.access_file(file_id=file_id, token=token))
        self.assertEqual(res.file_id, file_id)
        self.assertEqual(res.original_filename, "presentation.pdf")
        self.assertEqual(res.recipient_email, recipient)
        self.assertEqual(
            res.download_url,
            "https://s3.amazonaws.com/test-bucket/uploads/fid-123/presentation.pdf",
        )
        mock_add_access.assert_called_once_with(file_id, recipient)

    @patch("main.get_file_metadata")
    @patch("main.add_recipient_access")
    @patch("main.generate_presigned_get_url")
    def test_access_file_redirect(
        self,
        mock_get_url: MagicMock,
        mock_add_access: MagicMock,
        mock_get_meta: MagicMock,
    ) -> None:
        file_id = "fid-123"
        recipient = "alice@example.com"
        token = auth.generate_recipient_token(file_id, recipient)

        mock_get_meta.return_value = {
            "file_id": file_id,
            "original_filename": "presentation.pdf",
            "size_bytes": 2048,
            "content_type": "application/pdf",
            "s3_key": "uploads/fid-123/presentation.pdf",
            "recipients": [recipient],
            "accessed_by": [],
        }
        mock_get_url.return_value = (
            "https://s3.amazonaws.com/test-bucket/uploads/fid-123/presentation.pdf"
        )

        res = asyncio.run(
            main.access_file(file_id=file_id, token=token, redirect=True)
        )
        self.assertEqual(res.status_code, 307)
        self.assertEqual(
            res.headers["location"],
            "https://s3.amazonaws.com/test-bucket/uploads/fid-123/presentation.pdf",
        )

    @patch("main.get_file_metadata")
    def test_access_file_not_found(self, mock_get_meta: MagicMock) -> None:
        mock_get_meta.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(main.access_file(file_id="non-existent", token="any"))
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("main.get_file_metadata")
    def test_access_file_invalid_token(self, mock_get_meta: MagicMock) -> None:
        mock_get_meta.return_value = {
            "file_id": "fid-123",
            "recipients": ["alice@example.com"],
        }
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(main.access_file(file_id="fid-123", token="invalid-token"))
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("main.get_file_metadata")
    @patch("main.add_recipient_access")
    def test_access_file_missing_s3_key(
        self, mock_add_access: MagicMock, mock_get_meta: MagicMock
    ) -> None:
        file_id = "fid-123"
        recipient = "alice@example.com"
        token = auth.generate_recipient_token(file_id, recipient)
        mock_get_meta.return_value = {
            "file_id": file_id,
            "recipients": [recipient],
        }
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(main.access_file(file_id=file_id, token=token))
        self.assertEqual(ctx.exception.status_code, 500)


if __name__ == "__main__":
    unittest.main()
