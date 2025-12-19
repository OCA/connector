# Read-Only Mode Implementation Summary

## Overview

This implementation adds a **Read-Only Mode** feature to the `connector_amazon_spapi`
module, enabling safe testing and verification of Amazon integration without making any
actual changes to the Amazon Seller Central account.

## Changes Made

### 1. Backend Model ([models/backend.py](models/backend.py))

Added new field:

- `read_only_mode` (Boolean): Flag to enable test-only mode where write operations are
  logged instead of executed
- Only visible when `test_mode` is enabled
- Default: False

### 2. Backend View ([views/backend_view.xml](views/backend_view.xml))

Added field to form view:

- `read_only_mode` field with `boolean_toggle` widget
- Conditionally visible when `test_mode` is True
- Positioned after `test_mode` field

### 3. Shop Model ([models/shop.py](models/shop.py))

Modified `push_stock()` method:

- Check `backend_id.read_only_mode` before creating and submitting feed
- When enabled: logs stock data preview and updates timestamp without API submission
- When disabled: normal behavior (create feed and submit to Amazon)

### 4. Order Model ([models/order.py](models/order.py))

Added three new methods:

#### `_get_last_done_picking()`

Helper method to find the most recent completed delivery picking for an order.

#### `push_shipment()`

New method to push shipment tracking to Amazon:

- Extracts tracking information from completed delivery picking
- Builds ORDER_FULFILLMENT feed XML with carrier and tracking details
- In read-only mode: logs tracking preview without submission
- In normal mode: creates feed and submits to Amazon
- Updates `last_shipment_push` timestamp
- Sets `shipment_confirmed` flag (only in normal mode)

#### `_build_fulfillment_feed_xml()`

Helper to build XML feed for order fulfillment notification according to Amazon's
schema.

### 5. Feed Model ([models/feed.py](models/feed.py))

Modified `submit_feed()` method:

- Check `backend_id.read_only_mode` at submission time
- When enabled: logs feed preview, sets state to "done" with special message
- When disabled: normal behavior (upload to S3, submit to Amazon API)

### 6. Documentation

Created two new documentation files:

#### [README_READ_ONLY_MODE.md](README_READ_ONLY_MODE.md)

Comprehensive guide covering:

- Feature overview and purpose
- How to enable read-only mode
- What operations are affected (reads vs writes)
- Detailed testing workflow
- Log output examples
- Troubleshooting guide
- Technical implementation details

#### Updated [README_IMPLEMENTATION.md](README_IMPLEMENTATION.md)

Added section about Test Mode and Read-Only Mode in configuration instructions.

## Feature Behavior

### Read Operations (Unaffected)

These continue to work normally:

- Product catalog sync (fetch listings from Amazon)
- Order import (pull orders and create in Odoo)
- Customer creation (from Amazon buyer data)
- Competitive pricing sync (fetch pricing data)
- ASIN/SKU linking (match products to Amazon offers)

### Write Operations (Logged in Read-Only Mode)

These are intercepted and logged:

- **Stock updates**: Logs inventory feed XML preview
- **Shipment tracking**: Logs fulfillment feed XML with tracking details
- **Feed submission**: Logs feed payload without API call

## Testing Workflow

1. Enable Test Mode and Read-Only Mode on backend
2. Sync catalog to verify SKU → Product mappings
3. Import orders to verify order creation and customer linking
4. Sync competitive prices to verify pricing data
5. Trigger stock push to verify stock calculations (logs only)
6. Complete deliveries and push shipments to verify tracking (logs only)
7. Review logs to ensure all data is correct
8. Disable Read-Only Mode to go live

## Log Output Examples

### Stock Push (Read-Only)

```
INFO [READ-ONLY MODE] Would push stock for 150 products to Amazon.
Feed XML preview:
<?xml version="1.0" encoding="UTF-8"?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
...
```

### Shipment Push (Read-Only)

```
INFO [READ-ONLY MODE] Would push shipment for Amazon order 123-4567890-1234567.
Tracking: FedEx 123456789012. Feed XML preview:
<?xml version="1.0" encoding="UTF-8"?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
...
```

### Feed Submission (Read-Only)

```
INFO [READ-ONLY MODE] Feed 42 (POST_INVENTORY_AVAILABILITY_DATA) would be
submitted to Amazon. Payload preview:
<?xml version="1.0" encoding="UTF-8"?>
...
```

## Benefits

1. **Safe Testing**: Verify all logic without affecting live Amazon account
2. **Data Validation**: Ensure product mappings, prices, and quantities are correct
3. **Workflow Testing**: Test complete integration workflow including cron jobs
4. **Debugging**: View exact XML that would be sent to Amazon
5. **Training**: Allow team members to learn system without risk
6. **Development**: Test new features or configuration changes safely

## Transition to Production

Once testing is complete:

1. Disable Read-Only Mode (keep Test Mode on)
2. Test single stock push manually
3. Verify feed in Amazon Seller Central
4. Test single shipment push
5. Monitor feed processing
6. Disable Test Mode for full production

## Technical Notes

- Minimal performance impact (single boolean check)
- Consistent logging with `[READ-ONLY MODE]` prefix
- No changes to security rules required
- Compatible with existing queue job system
- Cron jobs respect read-only mode automatically

## Files Modified

1. `models/backend.py` - Added `read_only_mode` field
2. `views/backend_view.xml` - Added field to UI
3. `models/shop.py` - Modified `push_stock()` method
4. `models/order.py` - Added shipment push methods
5. `models/feed.py` - Modified `submit_feed()` method
6. `README_READ_ONLY_MODE.md` - New comprehensive guide
7. `README_IMPLEMENTATION.md` - Updated with testing info

## Odoo Standards Compliance

✓ OCA coding style (PEP 8, proper imports, logging) ✓ Proper field definitions with help
text ✓ XML view follows Odoo conventions ✓ Uses `_logger.info()` for informational
messages ✓ No `print()` statements or debug code ✓ Descriptive docstrings for all
methods ✓ Type annotations where appropriate ✓ SQL constraints maintained ✓ Security
rules unchanged (appropriate)

## Version

Implemented for: **Odoo 16.0** Module Version: **16.0.1.0.0**
