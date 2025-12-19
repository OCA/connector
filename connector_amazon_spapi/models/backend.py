from odoo import api, fields, models


class AmazonBackend(models.Model):
    _name = "amazon.backend"
    _inherit = "connector.backend"
    _description = "Amazon SP-API Backend"

    @api.model
    def _select_versions(self):
        return [("spapi", "Selling Partner API")]

    name = fields.Char(required=True)
    code = fields.Char(help="Short code to identify this backend.")
    version = fields.Selection(
        selection=_select_versions, required=True, default="spapi"
    )
    seller_id = fields.Char(required=True, string="Seller ID")
    region = fields.Selection(
        selection=[("na", "North America"), ("eu", "Europe"), ("fe", "Far East")],
        required=True,
        default="na",
    )
    lwa_client_id = fields.Char(string="LWA Client ID", required=True)
    lwa_client_secret = fields.Char()
    lwa_refresh_token = fields.Char()
    aws_role_arn = fields.Char()
    aws_external_id = fields.Char(string="AWS External ID")
    endpoint = fields.Char(string="SP-API Endpoint")
    test_mode = fields.Boolean()
    enable_price_sync = fields.Boolean(default=True)
    enable_stock_sync = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse", string="Default Warehouse"
    )
    marketplace_ids = fields.One2many(
        comodel_name="amazon.marketplace",
        inverse_name="backend_id",
        string="Marketplaces",
    )
    shop_ids = fields.One2many(
        comodel_name="amazon.shop",
        inverse_name="backend_id",
        string="Shops",
    )
    note = fields.Text(string="Notes")

    # Access Token (temporary, refreshed automatically)
    access_token = fields.Char(readonly=True)
    token_expires_at = fields.Datetime(readonly=True)

    @api.model
    def _get_lwa_token_url(self):
        return "https://api.amazon.com/auth/o2/token"

    def _get_sp_api_endpoint(self):
        """Get SP-API endpoint based on region"""
        self.ensure_one()
        endpoints = {
            "na": "https://sellingpartnerapi-na.amazon.com",
            "eu": "https://sellingpartnerapi-eu.amazon.com",
            "fe": "https://sellingpartnerapi-fe.amazon.com",
        }
        return self.endpoint or endpoints.get(self.region)

    def _refresh_access_token(self):
        """Refresh LWA access token using refresh token"""
        self.ensure_one()
        from datetime import datetime, timedelta

        import requests

        from odoo.exceptions import UserError

        url = self._get_lwa_token_url()
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.lwa_refresh_token,
            "client_id": self.lwa_client_id,
            "client_secret": self.lwa_client_secret,
        }

        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            self.write(
                {
                    "access_token": data["access_token"],
                    "token_expires_at": datetime.now()
                    + timedelta(seconds=data["expires_in"] - 60),
                }
            )

            return data["access_token"]
        except Exception as e:
            raise UserError(f"Failed to refresh LWA access token: {str(e)}") from e

    def _get_access_token(self):
        """Get valid access token, refreshing if necessary"""
        self.ensure_one()
        from datetime import datetime

        if (
            not self.access_token
            or not self.token_expires_at
            or self.token_expires_at <= datetime.now()
        ):
            return self._refresh_access_token()

        return self.access_token

    def _call_sp_api(self, method, endpoint, params=None, json_data=None):
        """Make authenticated SP-API call"""
        self.ensure_one()
        import requests

        from odoo.exceptions import UserError

        access_token = self._get_access_token()
        url = f"{self._get_sp_api_endpoint()}{endpoint}"

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise UserError(
                f"SP-API HTTP Error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise UserError(f"SP-API Call Failed: {str(e)}") from e

    def action_test_connection(self):
        """Test SP-API connection by fetching marketplace participations"""
        self.ensure_one()

        try:
            result = self._call_sp_api(
                "GET",
                "/sellers/v1/marketplaceParticipations",
            )

            if result.get("payload"):
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Successful",
                        "message": (
                            f"Connected to Amazon SP-API. "
                            f"Found {len(result['payload'])} marketplace(s)."
                        ),
                        "type": "success",
                        "sticky": False,
                    },
                }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Failed",
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }
