# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
"""Test Amazon Feed lifecycle (submit, upload, status check, completion)."""

from unittest import mock

from .common import CommonConnectorAmazonSpapi


class TestFeedLifecycle(CommonConnectorAmazonSpapi):
    """Test complete feed submission and status monitoring workflow."""

    @mock.patch("odoo.addons.connector_amazon_spapi.models.feed.requests")
    def test_submit_feed_happy_path(self, mock_requests):
        """Test successful feed submission through all 4 steps."""
        # Setup mock responses
        mock_requests.put.return_value = mock.Mock(status_code=200)

        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Step 1: Create feed document response
            mock_call.side_effect = [
                {
                    "feedDocumentId": "TEST_DOC_123",
                    "url": "https://s3.example.com/upload",
                },
                # Step 3: Create feed response
                {"feedId": "TEST_FEED_456"},
            ]

            # Create feed record
            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "draft",
                    "payload_json": '<?xml version="1.0"?><test/>',
                }
            )

            # Submit feed
            feed.submit_feed()

            # Verify state transitions
            self.assertEqual(feed.state, "submitted")
            self.assertEqual(feed.external_feed_id, "TEST_FEED_456")

            # Verify API calls
            self.assertEqual(mock_call.call_count, 2)

            # Verify Step 1: Create feed document
            first_call = mock_call.call_args_list[0]
            self.assertEqual(first_call[0][0], "createFeedDocument")
            self.assertEqual(
                first_call[1]["json_data"]["contentType"],
                "text/xml; charset=UTF-8",
            )

            # Verify Step 2: Upload to S3
            mock_requests.put.assert_called_once()
            upload_call = mock_requests.put.call_args
            self.assertEqual(upload_call[0][0], "https://s3.example.com/upload")
            self.assertIn(b"<test/>", upload_call[1]["data"])

            # Verify Step 3: Create feed
            second_call = mock_call.call_args_list[1]
            self.assertEqual(second_call[0][0], "createFeed")
            self.assertEqual(
                second_call[1]["json_data"]["feedType"],
                "POST_INVENTORY_AVAILABILITY_DATA",
            )
            self.assertEqual(
                second_call[1]["json_data"]["inputFeedDocumentId"],
                "TEST_DOC_123",
            )

    @mock.patch("odoo.addons.connector_amazon_spapi.models.feed.requests")
    def test_submit_feed_create_document_error(self, mock_requests):
        """Test feed submission handles createFeedDocument API error."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Simulate API error on document creation
            mock_call.side_effect = Exception("API Error: Rate limit exceeded")

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "draft",
                    "payload_json": '<?xml version="1.0"?><test/>',
                }
            )

            # Submit should handle error gracefully
            with self.assertRaises(Exception) as cm:
                feed.submit_feed()

            self.assertIn("Rate limit exceeded", str(cm.exception))
            self.assertEqual(feed.state, "error")

    @mock.patch("odoo.addons.connector_amazon_spapi.models.feed.requests")
    def test_submit_feed_s3_upload_error(self, mock_requests):
        """Test feed submission handles S3 upload failure."""
        # Mock S3 upload failure
        mock_requests.put.return_value = mock.Mock(status_code=403, text="Forbidden")

        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Document creation succeeds
            mock_call.return_value = {
                "feedDocumentId": "TEST_DOC_123",
                "url": "https://s3.example.com/upload",
            }

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "draft",
                    "payload_json": '<?xml version="1.0"?><test/>',
                }
            )

            with self.assertRaises(Exception) as cm:
                feed.submit_feed()

            self.assertIn("403", str(cm.exception))
            self.assertEqual(feed.state, "error")

    def test_check_feed_status_in_progress(self):
        """Test status check when feed is still processing."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Mock IN_PROGRESS status
            mock_call.return_value = {
                "feedId": "TEST_FEED_456",
                "processingStatus": "IN_PROGRESS",
            }

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "submitted",
                    "external_feed_id": "TEST_FEED_456",
                }
            )

            # Check status
            feed.check_feed_status()

            # Verify still in progress
            self.assertEqual(feed.state, "in_progress")
            mock_call.assert_called_once_with(
                "getFeed",
                endpoint_params={"feedId": "TEST_FEED_456"},
            )

    def test_check_feed_status_done(self):
        """Test status check when feed processing completes successfully."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Mock DONE status
            mock_call.return_value = {
                "feedId": "TEST_FEED_456",
                "processingStatus": "DONE",
            }

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "in_progress",
                    "external_feed_id": "TEST_FEED_456",
                }
            )

            feed.check_feed_status()

            self.assertEqual(feed.state, "done")

    def test_check_feed_status_fatal_error(self):
        """Test status check when feed processing fails."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Mock FATAL status
            mock_call.return_value = {
                "feedId": "TEST_FEED_456",
                "processingStatus": "FATAL",
            }

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "in_progress",
                    "external_feed_id": "TEST_FEED_456",
                }
            )

            feed.check_feed_status()

            self.assertEqual(feed.state, "error")

    def test_check_feed_status_cancelled(self):
        """Test status check when feed is cancelled."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Mock CANCELLED status
            mock_call.return_value = {
                "feedId": "TEST_FEED_456",
                "processingStatus": "CANCELLED",
            }

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "in_progress",
                    "external_feed_id": "TEST_FEED_456",
                }
            )

            feed.check_feed_status()

            self.assertEqual(feed.state, "error")

    def test_check_feed_status_api_error(self):
        """Test status check handles API errors."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Simulate API error
            mock_call.side_effect = Exception("Network timeout")

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "in_progress",
                    "external_feed_id": "TEST_FEED_456",
                }
            )

            with self.assertRaisesRegex(Exception, "Network timeout"):
                feed.check_feed_status()

    def test_feed_retry_logic(self):
        """Test feed retry counter increments on status check."""
        with mock.patch.object(
            self.backend, "_call_sp_api", autospec=True
        ) as mock_call:
            # Mock IN_PROGRESS status
            mock_call.return_value = {
                "feedId": "TEST_FEED_456",
                "processingStatus": "IN_PROGRESS",
            }

            feed = self.env["amazon.feed"].create(
                {
                    "backend_id": self.backend.id,
                    "marketplace_id": self.marketplace.id,
                    "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                    "state": "in_progress",
                    "external_feed_id": "TEST_FEED_456",
                    "retry_count": 5,
                }
            )

            initial_retry = feed.retry_count
            feed.check_feed_status()

            # Verify retry counter increased
            self.assertEqual(feed.retry_count, initial_retry + 1)

    @mock.patch("odoo.addons.connector_amazon_spapi.models.feed.requests")
    def test_submit_feed_different_feed_types(self, mock_requests):
        """Test feed submission supports different feed types."""
        mock_requests.put.return_value = mock.Mock(status_code=200)

        feed_types = [
            "POST_INVENTORY_AVAILABILITY_DATA",
            "POST_ORDER_FULFILLMENT_DATA",
            "POST_PRODUCT_DATA",
        ]

        for feed_type in feed_types:
            with mock.patch.object(
                self.backend, "_call_sp_api", autospec=True
            ) as mock_call:
                mock_call.side_effect = [
                    {
                        "feedDocumentId": "TEST_DOC_123",
                        "url": "https://s3.example.com/upload",
                    },
                    {"feedId": "TEST_FEED_456"},
                ]

                feed = self.env["amazon.feed"].create(
                    {
                        "backend_id": self.backend.id,
                        "marketplace_id": self.marketplace.id,
                        "feed_type": feed_type,
                        "state": "draft",
                        "payload_json": '<?xml version="1.0"?><test/>',
                    }
                )

                feed.submit_feed()

                # Verify feed type was passed correctly
                create_feed_call = mock_call.call_args_list[1]
                self.assertEqual(
                    create_feed_call[1]["json_data"]["feedType"],
                    feed_type,
                )

    def test_multiple_feeds_independent(self):
        """Test multiple feeds can be submitted independently."""
        feed1 = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                "state": "draft",
                "payload_json": '<?xml version="1.0"?><feed1/>',
            }
        )

        feed2 = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "feed_type": "POST_ORDER_FULFILLMENT_DATA",
                "state": "draft",
                "payload_json": '<?xml version="1.0"?><feed2/>',
            }
        )

        # Verify feeds are independent
        self.assertNotEqual(feed1.id, feed2.id)
        self.assertEqual(feed1.state, "draft")
        self.assertEqual(feed2.state, "draft")
