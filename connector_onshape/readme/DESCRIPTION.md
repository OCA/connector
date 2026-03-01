This module provides bidirectional synchronization between Odoo and
[Onshape](https://www.onshape.com) cloud CAD/PLM platform.

It synchronizes:

- **Documents**: Import Onshape documents and their elements (part studios,
  assemblies, drawings).
- **Products**: Bind Onshape parts to Odoo products using a 4-strategy
  SKU matching algorithm (exact filename, part number, McMaster catalog,
  case-insensitive).
- **Bills of Materials**: Import Onshape assembly BOMs as `mrp.bom` records
  with component match scoring.
- **Metadata Export**: Push Odoo product SKUs and names back to Onshape
  part metadata (Part Number, Description fields).
- **Webhooks**: Receive real-time notifications from Onshape for metadata
  changes, workflow transitions, and revision creation.

The module uses the OCA Connector framework with queue_job for asynchronous
processing and supports both HMAC (API Key) and OAuth2 (App Store)
authentication modes.
