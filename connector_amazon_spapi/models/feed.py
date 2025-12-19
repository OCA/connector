# Copyright 2026 Kencove
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import logging
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AmazonFeed(models.Model):
    _name = "amazon.feed"
    _description = "Amazon Feed"

    name = fields.Char(required=True, default="New Feed")
    backend_id = fields.Many2one(
        comodel_name="amazon.backend",
        required=True,
        ondelete="cascade",
    )
    marketplace_id = fields.Many2one(
        comodel_name="amazon.marketplace", ondelete="set null"
    )
    feed_type = fields.Selection(
        selection=[
            ("POST_INVENTORY_AVAILABILITY_DATA", "Inventory"),
            ("POST_PRODUCT_PRICING_DATA", "Pricing"),
            ("POST_PRODUCT_DATA", "Product Data"),
            ("POST_ORDER_ACKNOWLEDGEMENT_DATA", "Order Acknowledgement"),
            ("POST_ORDER_FULFILLMENT_DATA", "Order Fulfillment"),
        ],
        required=True,
        default="POST_INVENTORY_AVAILABILITY_DATA",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("submitting", "Submitting"),
            ("submitted", "Submitted"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
    )
    external_feed_id = fields.Char(string="Amazon Feed ID")
    payload_json = fields.Text()
    last_state_message = fields.Char()
    retry_count = fields.Integer(default=0)
    last_status_update = fields.Datetime()

    def submit_feed(self):
        """Submit feed to Amazon SP-API via Feeds API.

        This is a queue job that:
        1. Creates the feed document
        2. Uploads the feed content
        3. Creates the feed
        4. Monitors feed processing status

        Ref: https://developer-docs.amazon.com/sp-api/docs/feeds-api-v2021-06-30-reference
        """
        self.ensure_one()

        if self.state not in ("draft", "error"):
            raise UserError(_("Feed must be in draft or error state to submit"))

        # Check if backend is in read-only mode
        if self.backend_id.read_only_mode:
            _logger.info(
                "[READ-ONLY MODE] Feed %s (%s) would be submitted to Amazon. "
                "Payload preview:\n%s",
                self.id,
                self.feed_type,
                self.payload_json[:1000]
                + ("..." if len(self.payload_json) > 1000 else ""),
            )
            self.write(
                {
                    "state": "done",
                    "last_status_update": datetime.now(),
                    "last_state_message": (
                        "READ-ONLY MODE: Feed not actually submitted to Amazon"
                    ),
                }
            )
            return

        try:
            self.write({"state": "submitting", "last_status_update": datetime.now()})

            # Use adapter for API calls via work_on context
            with self.backend_id.work_on("amazon.feed") as work:
                adapter = work.component(usage="feed.adapter")

                # Step 1: Create feed document to get upload destination
                create_doc_response = adapter.create_feed_document()
                feed_document_id = create_doc_response.get("feedDocumentId")
                upload_url = create_doc_response.get("url")

                # Step 2: Upload feed content to the presigned URL
                self._upload_feed_content(upload_url)

                # Step 3: Create the feed
                feed_response = adapter.create_feed(
                    feed_type=self.feed_type,
                    feed_document_id=feed_document_id,
                    marketplace_ids=[self.marketplace_id.marketplace_id],
                )
                self.external_feed_id = feed_response.get("feedId")

            self.write(
                {
                    "state": "submitted",
                    "last_status_update": datetime.now(),
                    "last_state_message": "Feed submitted successfully",
                }
            )

            # Step 4: Schedule status check job
            self.with_delay(eta=300).check_feed_status()

        except Exception as e:
            _logger.exception("Failed to submit feed %s", self.id)
            self.write(
                {
                    "state": "error",
                    "last_state_message": str(e),
                    "retry_count": self.retry_count + 1,
                    "last_status_update": datetime.now(),
                }
            )
            raise

    def _upload_feed_content(self, upload_url):
        """Upload feed XML content to presigned S3 URL.

        Args:
            upload_url: Presigned S3 URL from create feed document response
        """
        import requests

        headers = {"Content-Type": "text/xml; charset=UTF-8"}
        response = requests.put(
            upload_url,
            data=self.payload_json.encode("utf-8"),
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()

    def check_feed_status(self):
        """Check feed processing status and update state.

        GET /feeds/2021-06-30/feeds/{feedId}
        """
        self.ensure_one()

        if not self.external_feed_id:
            raise UserError(_("No external feed ID to check status"))

        try:
            # Use adapter for API calls via work_on context
            with self.backend_id.work_on("amazon.feed") as work:
                adapter = work.component(usage="feed.adapter")
                response = adapter.get_feed(self.external_feed_id)

            processing_status = response.get("processingStatus")

            state_mapping = {
                "CANCELLED": "error",
                "DONE": "done",
                "FATAL": "error",
                "IN_PROGRESS": "in_progress",
                "IN_QUEUE": "queued",
            }

            new_state = state_mapping.get(processing_status, "in_progress")

            self.write(
                {
                    "state": new_state,
                    "last_state_message": f"Processing status: {processing_status}",
                    "last_status_update": datetime.now(),
                }
            )

            # If still processing, schedule another check
            if new_state in ("queued", "in_progress"):
                self.with_delay(eta=300).check_feed_status()

        except Exception as e:
            _logger.exception("Failed to check feed status %s", self.external_feed_id)
            self.write(
                {
                    "state": "error",
                    "last_state_message": f"Status check failed: {str(e)}",
                    "last_status_update": datetime.now(),
                }
            )
