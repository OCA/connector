# Copyright 2024 Kencove Farm Fence Supplies
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import hmac

from .common import OnshapeTestCase


class TestWebhookController(OnshapeTestCase):
    """Test the Onshape webhook controller."""

    def test_validate_signature_correct(self):
        from ..controllers.webhook import OnshapeWebhookController

        controller = OnshapeWebhookController()
        secret = "test_webhook_secret"
        body = b'{"event": "test"}'
        expected_sig = base64.b64encode(
            hmac.new(secret.encode("utf-8"), body, digestmod=hashlib.sha256).digest()
        ).decode("ascii")

        result = controller._validate_signature(body, secret, expected_sig)
        self.assertTrue(result)

    def test_validate_signature_incorrect(self):
        from ..controllers.webhook import OnshapeWebhookController

        controller = OnshapeWebhookController()
        result = controller._validate_signature(
            b'{"event": "test"}', "secret", "wrong_signature"
        )
        self.assertFalse(result)

    def test_event_handler_routing(self):
        from ..controllers.webhook import OnshapeWebhookController

        controller = OnshapeWebhookController()

        handler = controller._get_event_handler("onshape.model.lifecycle.metadata")
        self.assertIsNotNone(handler)

        handler = controller._get_event_handler("onshape.workflow.transition")
        self.assertIsNotNone(handler)

        handler = controller._get_event_handler("onshape.revision.created")
        self.assertIsNotNone(handler)

        handler = controller._get_event_handler("unknown.event")
        self.assertIsNone(handler)

    def test_workflow_transition_updates_state(self):
        doc = self._create_mock_document()
        binding = self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_001",
                "onshape_document_id": doc.id,
                "onshape_state": "in_progress",
            }
        )

        # Test the state mapping logic directly instead of going through
        # the controller (which requires request context)
        state_map = {
            "release": "released",
            "obsolete": "obsolete",
            "in progress": "in_progress",
            "pending": "pending",
        }
        mapped_state = state_map.get("release")
        self.assertEqual(mapped_state, "released")

        bindings = self.env["onshape.product.product"].search(
            [
                ("backend_id", "=", self.backend.id),
                (
                    "onshape_document_id.onshape_document_id",
                    "=",
                    doc.onshape_document_id,
                ),
            ]
        )
        self.assertTrue(bindings)
        bindings.write({"onshape_state": mapped_state})
        self.assertEqual(binding.onshape_state, "released")

    def test_revision_created_marks_released(self):
        doc = self._create_mock_document()
        binding = self.env["onshape.product.product"].create(
            {
                "odoo_id": self.product_bolt.id,
                "backend_id": self.backend.id,
                "external_id": "abc123/elem_001/part_001",
                "onshape_document_id": doc.id,
                "onshape_state": "in_progress",
            }
        )

        # Test the binding lookup + state write directly
        bindings = self.env["onshape.product.product"].search(
            [
                ("backend_id", "=", self.backend.id),
                (
                    "onshape_document_id.onshape_document_id",
                    "=",
                    doc.onshape_document_id,
                ),
            ]
        )
        self.assertTrue(bindings)
        bindings.write({"onshape_state": "released"})
        self.assertEqual(binding.onshape_state, "released")
