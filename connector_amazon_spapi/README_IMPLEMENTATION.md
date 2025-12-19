# Amazon SP-API Connector - Implementation Guide

## Overview

The Amazon SP-API connector has been successfully scaffolded and installed with core
SP-API integration functionality.

## What's Been Implemented

### 1. Backend Model (`amazon.backend`)

**SP-API Authentication:**

- `_refresh_access_token()`: Refreshes LWA access token using refresh token
- `_get_access_token()`: Returns valid access token, auto-refreshing if expired
- `_call_sp_api()`: Makes authenticated HTTP requests to Amazon SP-API endpoints
- `action_test_connection()`: Tests API connection by fetching marketplace
  participations

**Credential Fields:**

- `seller_id`: Amazon Seller ID
- `region`: NA/EU/FE region selection
- `lwa_client_id`, `lwa_client_secret`, `lwa_refresh_token`: LWA credentials
- `aws_role_arn`, `aws_external_id`: AWS IAM role credentials (optional)
- `endpoint`: Custom API endpoint (auto-set based on region)
- `access_token`, `token_expires_at`: Cached access token

### 2. Shop Model (`amazon.shop`)

**Order Synchronization:**

- `action_sync_orders()`: Queues background job for order sync
- `sync_orders()`: Fetches orders from SP-API Orders endpoint
  - Uses `last_order_sync` timestamp or lookback days
  - Filters by marketplace and date range
  - Creates/updates order bindings via `amazon.sale.order`

**Stock Management:**

- `action_push_stock()`: Queues background job for stock push
- `push_stock()`: Placeholder for Feeds API integration (TODO)

**Configuration Fields:**

- `marketplace_id`: Target Amazon marketplace
- `import_orders`, `sync_stock`, `sync_price`: Feature toggles
- `include_afn`: Import Amazon-fulfilled orders
- `stock_policy`: Free vs forecast quantity
- `last_order_sync`: Last successful order sync timestamp
- `order_sync_lookback_days`: Default lookback period

### 3. Order Models (`amazon.sale.order`, `amazon.sale.order.line`)

**Order Binding:**

- Uses `external.binding` pattern with `_inherits` for `sale.order`
- `_create_or_update_from_amazon()`: Creates/updates Odoo orders from Amazon API data
- `_sync_order_lines()`: Fetches and imports order items
- `_get_or_create_partner()`: Partner matching logic (placeholder)

**Order Line Binding:**

- `_create_or_update_from_amazon()`: Creates/updates order lines from Amazon items
- `_get_product_by_sku()`: Maps Amazon SKU to Odoo products (placeholder)

**Amazon-Specific Fields:**

- `external_id` (AmazonOrderId), `purchase_date`, `last_update_date`
- `fulfillment_channel` (AFN/MFN), `status` (OrderStatus)
- `seller_sku`, `product_binding_id`

## Usage Guide

### Step 1: Configure Backend

1. Navigate to **Connectors > Amazon SP-API > Backends**
2. Create a new backend record:

   - **Name**: Your backend name (e.g., "Amazon US")
   - **Seller ID**: Your Amazon Seller ID
   - **Region**: Select NA, EU, or FE
   - **LWA Client ID**: From Amazon Developer Console
   - **LWA Client Secret**: From Amazon Developer Console
   - **LWA Refresh Token**: Generated via authorization flow
   - **Company**: Select your company
   - **Warehouse**: Default warehouse for orders

3. Save and click **Test Connection** button
   - Should display success message with marketplace count
   - If error, check credentials and endpoint configuration

### Step 2: Configure Shops

1. Navigate to **Connectors > Amazon SP-API > Shops**
2. Create shop records (one per marketplace):
   - **Name**: Shop name (e.g., "Amazon.com Shop")
   - **Backend**: Select your backend
   - **Marketplace**: Select target marketplace (e.g., ATVPDKIKX0DER for amazon.com)
   - **Import Orders**: Enable to sync orders
   - **Sync Stock**: Enable to push inventory
   - **Warehouse**: Override default warehouse if needed
   - **Pricelist**: Select pricelist for Amazon prices

### Step 3: Sync Orders

1. Open a shop record
2. Click **Sync Orders** button

   - Queues background job via `queue_job`
   - Job runs `sync_orders()` method asynchronously
   - Progress tracked via **Queue > Jobs** menu

3. Monitor sync:
   - Check **Last Order Sync** timestamp on shop
   - View created orders in **Sales > Orders**
   - Each order linked to `amazon.sale.order` binding

### Step 4: Review Imported Orders

1. Navigate to **Sales > Orders**
2. Filter by date or customer
3. Each Amazon order:
   - Linked to `amazon.sale.order` binding record
   - Contains Amazon Order ID in binding
   - Order lines mapped to products via SKU

## Architecture Notes

### Background Jobs

The connector uses `queue_job` with the `.with_delay()` pattern:

```python
# Queue a job
shop.with_delay().sync_orders()

# Job executes asynchronously
# Monitor in: Queue > Jobs menu
```

### External Binding Pattern

Orders use the `external.binding` pattern:

```python
class AmazonSaleOrder(models.Model):
    _name = "amazon.sale.order"
    _inherit = "external.binding"
    _inherits = {"sale.order": "odoo_id"}

    odoo_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    external_id = fields.Char()  # AmazonOrderId
```

This creates:

- 1 `sale.order` record (standard Odoo order)
- 1 `amazon.sale.order` binding (Amazon-specific data)
- Linked via `odoo_id` field

### API Rate Limits

Amazon SP-API has rate limits per endpoint:

- Orders API: 0.0167 requests/second (1 per minute)
- Use background jobs to respect limits
- Implement retry logic for throttling errors

## TODO / Future Enhancements

### Product Synchronization

- Implement product catalog import via Catalog Items API
- Map Amazon ASINs to Odoo products
- Sync product attributes, images, descriptions

### Stock Push (Feeds API)

- Build inventory feed XML
- Submit via `/feeds/2021-06-30/feeds`
- Poll feed processing status
- Handle feed result reports

### Price Push

- Implement pricing feed submission
- Support competitive pricing rules
- Handle bulk price updates

### Partner Matching

- Enhance `_get_or_create_partner()` logic
- Match by email, phone, or address
- Create new partners for unknown buyers

### Error Handling

- Implement retry mechanism for API errors
- Log failed syncs for debugging
- Email notifications for critical failures

### Advanced Features

- Fulfillment (FBA) order handling
- Returns and refunds via RMA API
- Multi-currency support
- Tax calculation

## API Documentation

- **SP-API Developer Guide**: https://developer-docs.amazon.com/sp-api/
- **Orders API**: https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference
- **Feeds API**: https://developer-docs.amazon.com/sp-api/docs/feeds-api-reference
- **Catalog Items API**:
  https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-v2020-12-01-reference

## Support

For issues or questions:

1. Check Odoo logs: `invoke logs`
2. Review background jobs: **Queue > Jobs**
3. Verify API credentials and permissions
4. Check Amazon Seller Central for account status
