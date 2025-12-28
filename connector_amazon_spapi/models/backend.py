import logging

from sp_api.api import Sellers

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
    seller_sku = fields.Char(required=True, string="Seller SKU")
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
    read_only_mode = fields.Boolean(
        string="Read-Only Mode (Testing)",
        default=False,
        help=(
            "When enabled, all write operations to Amazon (stock updates, "
            "shipment tracking, etc.) will be logged instead of actually "
            "submitted. Use this for testing and verification without "
            "affecting your Amazon account."
        ),
    )
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

    def _get_sp_api_endpoint(self):
        """Get SP-API endpoint based on region"""
        self.ensure_one()
        endpoints = {
            "na": "https://sellingpartnerapi-na.amazon.com",
            "eu": "https://sellingpartnerapi-eu.amazon.com",
            "fe": "https://sellingpartnerapi-fe.amazon.com",
        }
        return self.endpoint or endpoints.get(self.region)

    def get_credentials(self):
        credentials = dict(
            refresh_token=self.lwa_refresh_token,
            lwa_app_id=self.lwa_client_id,
            lwa_client_secret=self.lwa_client_secret,
        )
        return credentials

    def action_test_connection(self):
        """Test SP-API connection by fetching marketplace participations"""
        self.ensure_one()

        try:
            client = Sellers(credentials=self.get_credentials())
            result = client.get_marketplace_participation()
            if result.payload:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Connection Successful",
                        "message": (
                            f"Connected to Amazon SP-API. "
                            f"Found {len(result.payload)} marketplace(s)."
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

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Connection Failed",
                "message": "No marketplaces returned by SP-API.",
                "type": "warning",
                "sticky": False,
            },
        }

    def action_fetch_marketplaces(self):
        """Fetch marketplaces from SP-API and upsert records.

        Uses ``/sellers/v1/marketplaceParticipations`` to discover the
        marketplaces this seller participates in, then creates or updates
        ``amazon.marketplace`` entries linked to this backend.
        """
        self.ensure_one()

        client = Sellers(credentials=self.get_credentials())
        result = client.get_marketplace_participation()
        payload = result.payload or []

        if not payload:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "No Marketplaces",
                    "message": "No marketplace participations returned by SP-API.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        Marketplace = self.env["amazon.marketplace"]
        Currency = self.env["res.currency"]

        created = 0
        updated = 0

        for item in payload:
            marketplace = item.get("marketplace", {})
            marketplace_id = marketplace.get("id")
            if not marketplace_id:
                continue

            country_code = (marketplace.get("countryCode") or "").upper()
            currency_code = marketplace.get("defaultCurrencyCode")
            name = marketplace.get("name") or marketplace_id

            currency = False
            if currency_code:
                currency = Currency.search([("name", "=", currency_code)], limit=1)

            vals = {
                "name": name,
                "code": country_code,
                "marketplace_id": marketplace_id,
                "backend_id": self.id,
                "country_code": country_code,
                "region": self.region,
            }
            if currency:
                vals["currency_id"] = currency.id

            # Prefer the already-linked marketplaces to avoid missing the
            # record when the database search ignores an unflushed cache.
            existing = self.marketplace_ids.filtered(
                lambda m: m.marketplace_id == marketplace_id
            )
            if not existing:
                existing = Marketplace.search(
                    [
                        ("backend_id", "=", self.id),
                        ("marketplace_id", "=", marketplace_id),
                    ],
                    limit=1,
                )

            if existing:
                existing.write(vals)
                updated += 1
            else:
                Marketplace.create(vals)
                created += 1

        if created or updated:
            # Log the update/create event to the Odoo server log
            _logger.info(
                "[AmazonBackend] Created %d, updated %d marketplace(s) for backend ID %s",
                created,
                updated,
                self.id,
            )
            # Notify success and reload form to display fetched marketplaces
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Marketplaces Synced",
                    "message": f"Created {created}, updated {updated} marketplace(s).",
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.client",
                        "tag": "reload",
                    },
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Marketplaces Synced",
                    "message": "No marketplaces created or updated.",
                    "type": "info",
                    "sticky": False,
                },
            }
