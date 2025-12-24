# Amazon SP-API Connector - Read-Only Mode

## Overview

The **Read-Only Mode** feature enables safe testing and verification of the Amazon
SP-API connector without making any actual changes to your Amazon Seller Central
account.

When enabled, all write operations to Amazon (stock updates, shipment tracking, etc.)
are intercepted and logged instead of being submitted to Amazon's API. This allows you
to verify:

- Product SKU mappings and ASIN linkages
- Order imports and customer creation
- Competitive pricing data synchronization
- Stock calculation logic
- Shipment tracking data extraction

All without affecting your live Amazon account.

## Enabling Read-Only Mode

1. Navigate to **Amazon > Configuration > Backends**
2. Open your Amazon backend record
3. Enable **Test Mode** checkbox
4. Enable **Read-Only Mode (Testing)** checkbox (visible when Test Mode is on)
5. Save the backend

**Important**: Read-Only Mode is only visible and functional when Test Mode is enabled.

## What Happens in Read-Only Mode

### Read Operations (Unaffected)

These operations continue to work normally and pull data from Amazon:

- **Product Catalog Sync**: Fetches Amazon listings and creates/updates product bindings
- **Order Import**: Pulls orders from Amazon and creates sale orders in Odoo
- **Customer Creation**: Creates partner records from Amazon buyer information
- **Competitive Pricing**: Fetches pricing data from Amazon competitors
- **ASIN/SKU Linking**: Links Odoo products to Amazon offers via SKU and ASIN

### Write Operations (Logged Only)

These operations are intercepted and logged instead of submitted to Amazon:

#### 1. Stock Level Updates

When `Shop.push_stock()` is called:

- Calculates available quantities for all synced products
- Builds inventory feed XML according to Amazon specifications
- **Logs** the feed XML (first 1000 characters) to Odoo logs
- Updates `last_stock_sync` timestamp (for testing workflow)
- **Does NOT** create feed record or submit to Amazon

Example log output:

```
[READ-ONLY MODE] Would push stock for 150 products to Amazon.
Feed XML preview:
<?xml version="1.0" encoding="UTF-8"?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
  <Header>
    <DocumentVersion>1.01</DocumentVersion>
    <MerchantIdentifier>A123456789</MerchantIdentifier>
  </Header>
  <MessageType>Inventory</MessageType>
  <Message>
    <MessageID>1</MessageID>
    <Inventory>
      <SKU>PRODUCT-001</SKU>
      <Quantity>
        <Available>100</Available>
      </Quantity>
    </Inventory>
  </Message>
...
```

#### 2. Shipment Tracking Updates

When `AmazonSaleOrder.push_shipment()` is called:

- Identifies the completed delivery picking
- Extracts carrier name and tracking reference
- Builds fulfillment feed XML with tracking information
- **Logs** the tracking details and feed XML preview
- Updates `last_shipment_push` timestamp
- **Does NOT** create feed record or submit to Amazon
- **Does NOT** mark `shipment_confirmed` as True (stays testable)

Example log output:

```
[READ-ONLY MODE] Would push shipment for Amazon order 123-4567890-1234567.
Tracking: FedEx 123456789012. Feed XML preview:
<?xml version="1.0" encoding="UTF-8"?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">
  <Header>
    <DocumentVersion>1.01</DocumentVersion>
    <MerchantIdentifier>A123456789</MerchantIdentifier>
  </Header>
  <MessageType>OrderFulfillment</MessageType>
  <Message>
    <MessageID>1</MessageID>
    <OrderFulfillment>
      <AmazonOrderID>123-4567890-1234567</AmazonOrderID>
      <FulfillmentDate>2025-12-24T15:30:00</FulfillmentDate>
      <FulfillmentData>
        <CarrierName>FedEx</CarrierName>
...
```

#### 3. Feed Submission

When `AmazonFeed.submit_feed()` is called:

- Validates feed state
- **Logs** feed type and payload preview
- Sets feed state to "done" with message indicating read-only mode
- **Does NOT** call Amazon SP-API
- **Does NOT** upload to S3
- **Does NOT** schedule status check jobs

Example log output:

```
[READ-ONLY MODE] Feed 42 (POST_INVENTORY_AVAILABILITY_DATA) would be submitted to Amazon.
Payload preview:
<?xml version="1.0" encoding="UTF-8"?>
<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
...
```

## Testing Workflow

### 1. Initial Setup

1. Enable Read-Only Mode on your backend
2. Configure shops with appropriate marketplaces
3. Set up warehouse, pricelist, and other shop settings

### 2. Product Synchronization

Run catalog sync to verify SKU → Product mapping:

```python
# From Odoo shell or automated action
shop = env['amazon.shop'].browse(1)
shop.sync_catalog()
```

Expected results:

- Product bindings created for products with matching SKUs
- ASINs linked to products
- Warnings logged for unmapped SKUs

Verify:

- Check `amazon.product.binding` records
- Ensure `seller_sku` and `asin` fields are populated
- Verify `sync_stock` and `sync_price` flags are set

### 3. Order Import

Run order sync to verify order creation:

```python
shop.sync_orders()
```

Expected results:

- Sale orders created in Odoo
- Customer partners created with Amazon buyer info
- Order lines linked to products via SKU
- Amazon order binding records created

Verify:

- Check created sale orders have correct products, quantities, prices
- Verify customer addresses and contact information
- Confirm order lines are linked to product bindings

### 4. Competitive Pricing

Run pricing sync to verify data fetching:

```python
shop.sync_competitive_prices()
```

Expected results:

- Competitive price records created
- ASIN-based pricing data stored
- `last_price_sync` timestamp updated

### 5. Stock Push (Logged Only)

Trigger stock push to verify stock calculation:

```python
shop.push_stock()
```

Expected results:

- **No feed record created**
- **No API calls made**
- Log entry with stock levels for each product
- `last_stock_sync` timestamp updated

Check logs for:

- Correct quantity calculations (qty_available - stock_buffer)
- Proper XML structure
- All synced products included

### 6. Shipment Tracking (Logged Only)

Complete a delivery and trigger shipment push:

```python
order_binding = env['amazon.sale.order'].search([('external_id', '=', 'AMAZON-ORDER-ID')])
order_binding.push_shipment()
```

Expected results:

- **No feed record created**
- **No API calls made**
- Log entry with tracking details
- `last_shipment_push` updated
- `shipment_confirmed` remains False (testable)

Check logs for:

- Correct carrier name extracted
- Tracking reference present
- Proper order line item mapping in XML

## Transitioning to Production

Once testing is complete and verified:

1. **Disable Read-Only Mode** on the backend (keep Test Mode on initially)
2. Test a single stock push manually to verify API connectivity
3. Verify the feed appears in Amazon Seller Central
4. Test a single shipment push
5. Monitor feed processing status
6. **Disable Test Mode** to go fully live
7. Enable scheduled cron jobs for automatic synchronization

## Cron Jobs Behavior

Cron jobs respect Read-Only Mode:

- **Stock Push Cron**: Runs but only logs (no actual submissions)
- **Order Import Cron**: Runs normally (read operations unaffected)
- **Shipment Push Cron**: Runs but only logs (no actual submissions)
- **Competitive Pricing Cron**: Runs normally (read operations unaffected)

This allows you to test the complete workflow including scheduled jobs.

## Troubleshooting

### No logs appearing

Check Odoo log level is set to INFO or DEBUG:

```
--log-level=info
```

Or check server logs for entries starting with `[READ-ONLY MODE]`

### Stock levels look incorrect

Verify:

- `product.product.qty_available` values are correct
- `amazon.product.binding.stock_buffer` is set appropriately
- Warehouse configuration matches shop configuration

### Tracking not extracted

Verify:

- Delivery order has `carrier_id` set
- Delivery order has `carrier_tracking_ref` populated
- Delivery order is in 'done' state
- Picking type is 'outgoing' to customer location

### Orders not importing

This indicates an issue with read operations (unaffected by Read-Only Mode):

- Check backend credentials are valid
- Verify marketplace configuration
- Check API rate limits
- Review error logs for authentication issues

## Technical Details

### Implementation Notes

Read-Only Mode is implemented at three levels:

1. **Shop Model** (`shop.py`):

   - `push_stock()`: Checks `backend_id.read_only_mode` before feed creation

2. **Order Model** (`order.py`):

   - `push_shipment()`: Checks `backend_id.read_only_mode` before feed creation
   - `_get_last_done_picking()`: Helper to find shipped delivery
   - `_build_fulfillment_feed_xml()`: Builds tracking feed XML

3. **Feed Model** (`feed.py`):
   - `submit_feed()`: Checks `backend_id.read_only_mode` at feed submission time
   - Marks feed as "done" with special message in read-only mode

### Logging Strategy

All read-only mode logs use Python's `logging` module at INFO level:

```python
_logger.info("[READ-ONLY MODE] ...")
```

This ensures visibility in standard Odoo logs while being filterable.

### Performance Considerations

Read-Only Mode has minimal performance impact:

- No additional database queries (single field check)
- No API calls prevented (the main benefit)
- Slightly more log I/O (negligible)

The primary benefit is preventing accidental API calls during testing, which:

- Protects your Amazon account from test data
- Avoids API rate limit consumption
- Prevents customer confusion from test shipments

## Related Features

- **Test Mode**: General testing flag (must be enabled for Read-Only Mode)
- **Enable Stock Sync**: Controls whether stock push is enabled at all
- **Enable Price Sync**: Controls whether price updates are enabled
- **Stock Sync Interval**: Controls frequency of automatic stock pushes

## Version History

- **16.0.1.0.0**: Initial implementation of Read-Only Mode feature
