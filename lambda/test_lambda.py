"""Unit tests for the lifecycle auto-deletion Lambda handler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import MagicMock, patch

import lambda_function


class TestLambdaLifecycle(unittest.TestCase):
    """Unit tests for lifecycle rules and lambda execution."""

    def setUp(self) -> None:
        """Clear cached settings before each test run."""
        lambda_function.get_settings.cache_clear()

    def test_should_delete_all_accessed(self) -> None:
        """Verify that item with all recipients accessed triggers deletion."""
        item = {
            "file_id": "fid-1",
            "recipients": ["alice@test.com", "bob@test.com"],
            "accessed_by": ["alice@test.com", "bob@test.com"],
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        del_ready, reason = lambda_function.should_delete(item)
        self.assertTrue(del_ready)
        self.assertEqual(reason, "all_recipients_accessed")

    def test_should_delete_pending_retained(self) -> None:
        """Verify that item with pending recipients is retained."""
        item = {
            "file_id": "fid-2",
            "recipients": ["alice@test.com", "bob@test.com"],
            "accessed_by": ["alice@test.com"],
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        del_ready, reason = lambda_function.should_delete(item)
        self.assertFalse(del_ready)
        self.assertEqual(reason, "retained")

    def test_should_delete_hard_expiry(self) -> None:
        """Verify that item exceeding hard expiry is marked for deletion."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        item = {
            "file_id": "fid-3",
            "recipients": ["alice@test.com"],
            "accessed_by": [],
            "uploaded_at": old_time,
        }
        del_ready, reason = lambda_function.should_delete(item, expiry_days=30)
        self.assertTrue(del_ready)
        self.assertIn("hard_expiry", reason)

    @patch("lambda_function.get_s3_client")
    @patch("lambda_function.get_dynamo_resource")
    def test_lambda_handler_execution(
        self,
        mock_get_dynamo: MagicMock,
        mock_get_s3: MagicMock,
    ) -> None:
        """Verify lambda_handler deletes eligible files and updates scan counts."""
        mock_s3 = MagicMock()
        mock_get_s3.return_value = mock_s3

        mock_dynamo = MagicMock()
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table
        mock_get_dynamo.return_value = mock_dynamo

        # item 1: completed, item 2: pending
        mock_table.scan.return_value = {
            "Items": [
                {
                    "file_id": "fid-completed",
                    "s3_key": "uploads/fid-completed/file.pdf",
                    "recipients": ["alice@test.com"],
                    "accessed_by": ["alice@test.com"],
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "file_id": "fid-pending",
                    "s3_key": "uploads/fid-pending/file2.pdf",
                    "recipients": ["bob@test.com"],
                    "accessed_by": [],
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
        }

        expected_bucket = lambda_function.get_settings().S3_BUCKET_NAME
        res = lambda_function.lambda_handler()
        self.assertEqual(res["statusCode"], 200)
        self.assertEqual(res["scanned"], 2)
        self.assertEqual(res["deleted"], 1)

        mock_s3.delete_object.assert_called_once_with(
            Bucket=expected_bucket,
            Key="uploads/fid-completed/file.pdf",
        )
        mock_table.delete_item.assert_called_once_with(
            Key={"file_id": "fid-completed"}
        )


if __name__ == "__main__":
    unittest.main()
