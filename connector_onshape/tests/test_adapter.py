# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch

from .common import OnshapeTestCase


class TestOnshapeAdapter(OnshapeTestCase):
    """Test the HMAC signing logic and adapter methods."""

    def _get_adapter_component(self):
        with self.backend.work_on("onshape.backend") as work:
            return work.component(usage="backend.adapter")

    def test_hmac_header_generation(self):
        adapter = self._get_adapter_component()
        headers = adapter._hmac_headers("GET", "/api/v6/documents")

        self.assertIn("Authorization", headers)
        self.assertIn("Date", headers)
        self.assertIn("On-Nonce", headers)
        self.assertTrue(
            headers["Authorization"].startswith("On test_api_key:HmacSHA256:")
        )

    def test_hmac_signature_correctness(self):
        adapter = self._get_adapter_component()
        headers = adapter._hmac_headers(
            "GET",
            "/api/v6/documents",
            query_params={"limit": "1"},
            content_type="",
        )

        # Verify the signature structure
        auth = headers["Authorization"]
        parts = auth.split(":")
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], "On test_api_key")
        self.assertEqual(parts[1], "HmacSHA256")
        # Verify base64 decoding works
        sig_bytes = base64.b64decode(parts[2])
        self.assertEqual(len(sig_bytes), 32)  # SHA256 = 32 bytes

    def test_canonical_query(self):
        adapter = self._get_adapter_component()
        self.assertEqual(adapter._canonical_query(None), "")
        self.assertEqual(adapter._canonical_query({}), "")
        result = adapter._canonical_query({"b": "2", "a": "1"})
        self.assertEqual(result, "a=1&b=2")

    @patch("odoo.addons.connector_onshape.components.adapter.requests")
    def test_check_credentials_success(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        mock_requests.request.return_value = mock_resp

        adapter = self._get_adapter_component()
        ok, msg = adapter.check_credentials()
        self.assertTrue(ok)
        self.assertIn("verified", msg.lower())

    @patch("odoo.addons.connector_onshape.components.adapter.requests")
    def test_check_credentials_unauthorized(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_requests.request.return_value = mock_resp

        adapter = self._get_adapter_component()
        ok, msg = adapter.check_credentials()
        self.assertFalse(ok)
        self.assertIn("401", msg)

    @patch("odoo.addons.connector_onshape.components.adapter.requests.request")
    def test_quota_exhausted_raises(self, mock_request):
        from ..components.adapter import OnshapeQuotaError

        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        adapter = self._get_adapter_component()
        with self.assertRaises(OnshapeQuotaError):
            adapter._request("GET", "/api/v6/documents")
