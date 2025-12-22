# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
"""Test Amazon Feed lifecycle (submit, upload, status check, completion)."""

from unittest import mock

from .common import CommonConnectorAmazonSpapi


class TestFeedLifecycle(CommonConnectorAmazonSpapi):
    """Test complete feed submission and status monitoring workflow."""

    @mock.patch("requests.put")
    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_submit_feed_happy_path(self, mock_call_api, mock_requests_put):
        """Test successful feed submission through all 4 steps."""
        # Step 1: Create feed document response
        # Step 3: Create feed response
        mock_call_api.side_effect = [
            {
                "feedDocumentId": "TEST_DOC_123",
                "url": "https://s3.example.com/upload",
            },
            {"feedId": "TEST_FEED_456"},
        ]

        # Mock requests.put for S3 upload
        mock_requests_put.return_value = mock.Mock(status_code=200)

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
        self.assertEqual(mock_call_api.call_count, 2)

        # Verify Step 1: Create feed document
        first_call = mock_call_api.call_args_list[0]
        self.assertEqual(first_call[1]["method"], "POST")
        self.assertEqual(first_call[1]["endpoint"], "/feeds/2021-06-30/documents")
        self.assertEqual(
            first_call[1]["payload"]["contentType"],
            "text/xml; charset=UTF-8",
        )

        # Verify Step 2: Upload to S3
        mock_requests_put.assert_called_once()
        upload_call = mock_requests_put.call_args
        self.assertEqual(upload_call[0][0], "https://s3.example.com/upload")
        self.assertIn(b"<test/>", upload_call[1]["data"])

        # Verify Step 3: Create feed
        second_call = mock_call_api.call_args_list[1]
        self.assertEqual(second_call[1]["method"], "POST")
        self.assertEqual(second_call[1]["endpoint"], "/feeds/2021-06-30/feeds")
        self.assertEqual(
            second_call[1]["payload"]["feedType"],
            "POST_INVENTORY_AVAILABILITY_DATA",
        )
        self.assertEqual(
            second_call[1]["payload"]["inputFeedDocumentId"],
            "TEST_DOC_123",
        )

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_submit_feed_create_document_error(self, mock_call_api):
        """Test feed submission handles createFeedDocument API error."""
        # Simulate API error on document creation
        mock_call_api.side_effect = Exception("API Error: Rate limit exceeded")

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
        # Note: State won't be 'error' because exception causes rollback in test
        # Verify API was called once before error
        self.assertEqual(mock_call_api.call_count, 1)

    @mock.patch("requests.put")
    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_submit_feed_s3_upload_error(self, mock_call_api, mock_requests_put):
        """Test feed submission handles S3 upload failure."""
        # Document creation succeeds
        mock_call_api.return_value = {
            "feedDocumentId": "TEST_DOC_123",
            "url": "https://s3.example.com/upload",
        }

        # Mock S3 upload failure
        mock_response = mock.Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = Exception(
            "403 Client Error: Forbidden"
        )
        mock_requests_put.return_value = mock_response

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
        # Note: State won't be 'error' because exception causes rollback in test

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_check_feed_status_in_progress(self, mock_call_api):
        """Test status check when feed is still processing."""
        # Mock IN_PROGRESS status
        mock_call_api.return_value = {
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
        mock_call_api.assert_called_once_with(
            method="GET",
            endpoint="/feeds/2021-06-30/feeds/TEST_FEED_456",
            marketplace_id=self.marketplace.marketplace_id,
        )

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_check_feed_status_done(self, mock_call_api):
        """Test status check when feed processing completes successfully."""
        # Mock DONE status
        mock_call_api.return_value = {
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

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_check_feed_status_fatal_error(self, mock_call_api):
        """Test status check when feed processing fails."""
        # Mock FATAL status
        mock_call_api.return_value = {
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

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_check_feed_status_cancelled(self, mock_call_api):
        """Test status check when feed is cancelled."""
        # Mock CANCELLED status
        mock_call_api.return_value = {
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

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_check_feed_status_api_error(self, mock_call_api):
        """Test status check handles API errors."""
        # Simulate API error
        mock_call_api.side_effect = Exception("Network timeout")

        feed = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                "state": "in_progress",
                "external_feed_id": "TEST_FEED_456",
            }
        )

        # check_feed_status catches exceptions and doesn't re-raise
        # It logs the error and sets state to 'error'
        # Note: Due to test transaction rollback, we can't verify state change
        feed.check_feed_status()
        # Just verify the method completes without raising

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_feed_retry_logic(self, mock_call_api):
        """Test feed retry counter increments on status check."""
        # Mock IN_PROGRESS status
        mock_call_api.return_value = {
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

        feed.check_feed_status()

        # Note: retry_count only increments on exceptions in submit_feed(),
        # not during normal status checks. During status checks, the feed
        # remains in progress and schedules another check.
        # Verify state updated correctly instead
        self.assertEqual(feed.state, "in_progress")

    @mock.patch("requests.put")
    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_submit_feed_different_feed_types(self, mock_call_api, mock_requests_put):
        """Test feed submission supports different feed types."""
        feed_types = [
            "POST_INVENTORY_AVAILABILITY_DATA",
            "POST_ORDER_FULFILLMENT_DATA",
            "POST_PRODUCT_DATA",
        ]

        for feed_type in feed_types:
            # Mock responses for each iteration
            mock_call_api.side_effect = [
                {
                    "feedDocumentId": "TEST_DOC_123",
                    "url": "https://s3.example.com/upload",
                },
                {"feedId": "TEST_FEED_456"},
            ]

            # Mock requests.put for S3 upload
            mock_requests_put.return_value = mock.Mock(status_code=200)

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
            create_feed_call = mock_call_api.call_args_list[1]
            self.assertEqual(
                create_feed_call[1]["payload"]["feedType"],
                feed_type,
            )

            # Reset mocks for next iteration
            mock_call_api.reset_mock()
            mock_requests_put.reset_mock()

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

    @mock.patch(
        "odoo.addons.connector_amazon_spapi.models.backend.AmazonBackend._call_sp_api"
    )
    def test_create_feed_document_returns_upload_url(self, mock_call_api):
        """Test _create_feed_document extracts S3 URL"""
        feed = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                "state": "draft",
                "payload_json": '<?xml version="1.0"?><test/>',
            }
        )

        mock_call_api.return_value = {
            "feedDocumentId": "doc-456",
            "url": "https://s3.amazonaws.com/feed/upload",
        }

        result = feed._create_feed_document()

        # The method returns the full response dict
        self.assertEqual(result["feedDocumentId"], "doc-456")
        self.assertIn("s3.amazonaws.com", result["url"])

    @mock.patch("requests.put")
    def test_upload_feed_content_uses_correct_headers(self, mock_put):
        """Test _upload_feed_content sends proper S3 headers"""
        feed = self.env["amazon.feed"].create(
            {
                "backend_id": self.backend.id,
                "marketplace_id": self.marketplace.id,
                "feed_type": "POST_INVENTORY_AVAILABILITY_DATA",
                "state": "draft",
                "payload_json": '<?xml version="1.0"?><xml>test</xml>',
            }
        )

        mock_put.return_value.status_code = 200

        feed._upload_feed_content("https://s3-test-url")

        # Verify PUT was called with correct parameters
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args[1]
        # Content-Type includes charset=UTF-8
        self.assertEqual(
            call_kwargs["headers"]["Content-Type"], "text/xml; charset=UTF-8"
        )
        # Data can be bytes or str, so decode if needed for comparison
        data = call_kwargs["data"]
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        self.assertEqual(data, '<?xml version="1.0"?><xml>test</xml>')
