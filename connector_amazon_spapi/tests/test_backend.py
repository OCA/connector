# Copyright 2025 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, timedelta
from unittest import mock

from odoo.exceptions import UserError

from . import common


class TestAmazonBackend(common.CommonConnectorAmazonSpapi):
    """Tests for amazon.backend model"""

    def test_backend_creation(self):
        """Test creating a backend record"""
        self.assertEqual(self.backend.name, "Test Amazon Backend")
        self.assertEqual(self.backend.code, "test_amazon")
        self.assertEqual(self.backend.version, "spapi")
        self.assertEqual(self.backend.seller_id, "AKIAIOSFODNN7EXAMPLE")
        self.assertEqual(self.backend.region, "na")

    def test_get_lwa_token_url(self):
        """Test LWA token URL"""
        expected_url = "https://api.amazon.com/auth/o2/token"
        self.assertEqual(self.backend._get_lwa_token_url(), expected_url)

    def test_get_sp_api_endpoint_na(self):
        """Test SP-API endpoint for North America region"""
        backend = self._create_backend(region="na")
        expected = "https://sellingpartnerapi-na.amazon.com"
        self.assertEqual(backend._get_sp_api_endpoint(), expected)

    def test_get_sp_api_endpoint_eu(self):
        """Test SP-API endpoint for Europe region"""
        backend = self._create_backend(region="eu")
        expected = "https://sellingpartnerapi-eu.amazon.com"
        self.assertEqual(backend._get_sp_api_endpoint(), expected)

    def test_get_sp_api_endpoint_fe(self):
        """Test SP-API endpoint for Far East region"""
        backend = self._create_backend(region="fe")
        expected = "https://sellingpartnerapi-fe.amazon.com"
        self.assertEqual(backend._get_sp_api_endpoint(), expected)

    def test_get_sp_api_endpoint_custom(self):
        """Test SP-API endpoint with custom endpoint"""
        backend = self._create_backend(endpoint="https://custom.example.com")
        self.assertEqual(backend._get_sp_api_endpoint(), "https://custom.example.com")

    @mock.patch("requests.post")
    def test_refresh_access_token_success(self, mock_post):
        """Test successful access token refresh"""
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "Amzn1.obtainTokenResponse",
            "refresh_token": "Atzr|test-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token = self.backend._refresh_access_token()

        self.assertEqual(token, "Amzn1.obtainTokenResponse")
        self.backend.invalidate_recordset()
        self.assertEqual(self.backend.access_token, "Amzn1.obtainTokenResponse")
        self.assertIsNotNone(self.backend.token_expires_at)

        # Verify the request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.amazon.com/auth/o2/token")

    @mock.patch("requests.post")
    def test_refresh_access_token_failure(self, mock_post):
        """Test failed access token refresh"""
        mock_post.side_effect = Exception("Connection refused")

        with self.assertRaises(UserError) as cm:
            self.backend._refresh_access_token()

        self.assertIn("Failed to refresh LWA access token", str(cm.exception))

    @mock.patch("requests.post")
    def test_get_access_token_cached(self, mock_post):
        """Test getting cached access token"""
        # Set a cached token that hasn't expired
        future_time = datetime.now() + timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "cached-token-123",
                "token_expires_at": future_time,
            }
        )

        token = self.backend._get_access_token()

        self.assertEqual(token, "cached-token-123")
        mock_post.assert_not_called()

    @mock.patch("requests.post")
    def test_get_access_token_refresh_expired(self, mock_post):
        """Test getting access token when cached token is expired"""
        # Set an expired token
        past_time = datetime.now() - timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "expired-token-123",
                "token_expires_at": past_time,
            }
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "access_token": "new-token-456",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token = self.backend._get_access_token()

        self.assertEqual(token, "new-token-456")
        mock_post.assert_called_once()

    @mock.patch("requests.request")
    def test_call_sp_api_success(self, mock_request):
        """Test successful SP-API call"""
        # Set a valid cached token
        future_time = datetime.now() + timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "valid-token",
                "token_expires_at": future_time,
            }
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "payload": {
                "Orders": [{"AmazonOrderId": "ORDER-001", "OrderStatus": "Pending"}]
            }
        }
        mock_request.return_value = mock_response

        result = self.backend._call_sp_api(
            "GET",
            "/orders/v0/orders",
            params={"MarketplaceIds": "ATVPDKIKX0DER"},
        )

        self.assertIn("payload", result)
        self.assertIn("Orders", result["payload"])

        # Verify the request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]["method"], "GET")
        self.assertIn("/orders/v0/orders", call_args[1]["url"])
        self.assertIn("x-amz-access-token", call_args[1]["headers"])

    @mock.patch("requests.request")
    def test_call_sp_api_http_error(self, mock_request):
        """Test SP-API call with HTTP error"""
        future_time = datetime.now() + timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "valid-token",
                "token_expires_at": future_time,
            }
        )

        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_request.return_value = mock_response

        with self.assertRaises(UserError) as cm:
            self.backend._call_sp_api("GET", "/orders/v0/orders")

        self.assertIn("SP-API", str(cm.exception))

    @mock.patch("requests.request")
    def test_action_test_connection_success(self, mock_request):
        """Test successful connection test"""
        future_time = datetime.now() + timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "valid-token",
                "token_expires_at": future_time,
            }
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "payload": [
                {"MarketplaceId": "ATVPDKIKX0DER", "ParticipationStatus": "Active"},
                {"MarketplaceId": "A1F83G7XSQSF3T", "ParticipationStatus": "Active"},
            ]
        }
        mock_request.return_value = mock_response

        result = self.backend.action_test_connection()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")

    @mock.patch("requests.request")
    def test_action_test_connection_failure(self, mock_request):
        """Test failed connection test"""
        future_time = datetime.now() + timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "valid-token",
                "token_expires_at": future_time,
            }
        )

        mock_request.side_effect = UserError("Invalid credentials")

        result = self.backend.action_test_connection()

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "danger")

    @mock.patch("requests.request")
    def test_action_fetch_marketplaces_create_and_update(self, mock_request):
        """Fetch marketplaces creates new records and updates existing ones"""
        future_time = datetime.now() + timedelta(hours=1)
        self.backend.write(
            {
                "access_token": "valid-token",
                "token_expires_at": future_time,
            }
        )

        existing_marketplace = self.env["amazon.marketplace"].create(
            {
                "name": "Old US Name",
                "code": "US",
                "marketplace_id": "ATVPDKIKX0DER",
                "backend_id": self.backend.id,
                "country_code": "US",
                "region": self.backend.region,
            }
        )

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "payload": [
                {
                    "marketplace": {
                        "id": "ATVPDKIKX0DER",
                        "countryCode": "US",
                        "defaultCurrencyCode": "USD",
                        "name": "Amazon.com",
                    }
                },
                {
                    "marketplace": {
                        "id": "A1F83G7XSQSF3T",
                        "countryCode": "GB",
                        "defaultCurrencyCode": "GBP",
                        "name": "Amazon.co.uk",
                    }
                },
            ]
        }
        mock_request.return_value = mock_response

        result = self.backend.action_fetch_marketplaces()

        # Verify notification with success type
        self.assertEqual(result["params"]["type"], "success")
        # Verify reload action is chained via next
        self.assertEqual(result["params"]["next"]["type"], "ir.actions.client")
        self.assertEqual(result["params"]["next"]["tag"], "reload")

        updated = self.env["amazon.marketplace"].browse(existing_marketplace.id)
        self.assertEqual(updated.name, "Amazon.com")
        self.assertEqual(updated.country_code, "US")
        self.assertEqual(updated.region, self.backend.region)
        self.assertTrue(updated.currency_id)

        created = self.env["amazon.marketplace"].search(
            [
                ("marketplace_id", "=", "A1F83G7XSQSF3T"),
                ("backend_id", "=", self.backend.id),
            ],
            limit=1,
        )
        self.assertTrue(created)
        self.assertEqual(created.name, "Amazon.co.uk")
        self.assertEqual(created.country_code, "GB")
        self.assertEqual(created.region, self.backend.region)
        self.assertTrue(created.currency_id)

        request_kwargs = mock_request.call_args.kwargs
        self.assertEqual(request_kwargs["method"], "GET")
        self.assertIn("/sellers/v1/marketplaceParticipations", request_kwargs["url"])

    def test_backend_with_multiple_shops(self):
        """Test backend with multiple shops"""
        shop2 = self._create_shop(
            name="Test Amazon Shop 2",
            marketplace_id=self.env["amazon.marketplace"]
            .create(
                {
                    "name": "Amazon.co.uk",
                    "marketplace_id": "A1F83G7XSQSF3T",
                    "region": "EU",
                    "backend_id": self.backend.id,
                }
            )
            .id,
        )

        self.assertEqual(len(self.backend.shop_ids), 2)
        self.assertIn(self.shop, self.backend.shop_ids)
        self.assertIn(shop2, self.backend.shop_ids)

    def test_backend_warehouse_optional(self):
        """Test backend with optional warehouse"""
        backend_no_warehouse = self._create_backend(warehouse_id=None)
        self.assertFalse(backend_no_warehouse.warehouse_id)

        warehouse = self.env["stock.warehouse"].search([], limit=1)
        backend_with_warehouse = self._create_backend(warehouse_id=warehouse.id)
        self.assertEqual(backend_with_warehouse.warehouse_id, warehouse)
