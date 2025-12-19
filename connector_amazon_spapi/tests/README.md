# Amazon SP-API Connector - Test Suite

## Overview

This test suite provides comprehensive coverage for the Amazon SP-API Odoo connector
module, following OCA (Odoo Community Association) best practices and patterns from
existing Odoo connector modules.

## Test Structure

The test suite is organized into four main components:

### 1. **common.py** - Test Base Class and Fixtures

Provides `CommonConnectorAmazonSpapi` as the base class for all tests, inheriting from
`TransactionCase`.

**Key Features:**

- Isolated test database per test method
- Helper methods to create test fixtures:
  - `_create_backend()`: Creates test backend with SP-API credentials
  - `_create_marketplace()`: Creates marketplace records
  - `_create_shop()`: Creates shop with marketplace association
  - `_create_sample_amazon_order()`: Generates realistic Amazon order API data
  - `_create_sample_amazon_order_item()`: Generates realistic Amazon order item data

**Sample Data Includes:**

- Complete Amazon SP-API order structure with 22+ fields
- Order items with ASIN, SKU, pricing, and quantity information
- Realistic timestamps and status values
- Shipping address details

### 2. **test_backend.py** - Backend Model Tests (17 tests)

Tests for the `amazon.backend` model covering authentication, token management, and API
communication.

**Test Coverage:**

| Test                                    | Purpose                                              |
| --------------------------------------- | ---------------------------------------------------- |
| `test_backend_creation`                 | Verify backend record creation with correct fields   |
| `test_get_lwa_token_url`                | Verify LWA (Login with Amazon) token endpoint        |
| `test_get_sp_api_endpoint_na`           | Verify North America SP-API endpoint                 |
| `test_get_sp_api_endpoint_eu`           | Verify Europe SP-API endpoint                        |
| `test_get_sp_api_endpoint_fe`           | Verify Far East SP-API endpoint                      |
| `test_get_sp_api_endpoint_custom`       | Verify custom endpoint support                       |
| `test_refresh_access_token_success`     | Mock LWA refresh and verify token storage            |
| `test_refresh_access_token_failure`     | Verify error handling on refresh failure             |
| `test_get_access_token_cached`          | Verify token caching with TTL validation             |
| `test_get_access_token_refresh_expired` | Verify automatic refresh of expired tokens           |
| `test_call_sp_api_success`              | Mock SP-API call with auth headers                   |
| `test_call_sp_api_http_error`           | Verify HTTP error handling (401, 403, 500, etc.)     |
| `test_action_test_connection_success`   | Verify connection test with marketplace verification |
| `test_action_test_connection_failure`   | Verify error notification on test failure            |
| `test_backend_with_multiple_shops`      | Verify backend can support multiple shops            |
| `test_backend_warehouse_optional`       | Verify warehouse is optional field                   |
| Additional helpers and edge cases       | Token expiry calculations, endpoint selection        |

**Mock Usage:**

- `@mock.patch("requests.post")` - Mock LWA token endpoint
- `@mock.patch("requests.request")` - Mock SP-API calls

### 3. **test_shop.py** - Shop Model Tests (14 tests)

Tests for the `amazon.shop` model covering order synchronization and stock management.

**Test Coverage:**

| Test                                                 | Purpose                                                      |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| `test_shop_creation`                                 | Verify shop record creation                                  |
| `test_shop_defaults`                                 | Verify default values (import_orders=True, lookback_days=30) |
| `test_action_sync_orders_queues_job`                 | Verify queue_job is used for async sync                      |
| `test_sync_orders_fetches_from_api`                  | Mock SP-API orders endpoint and verify data fetch            |
| `test_sync_orders_respects_import_orders_flag`       | Verify sync skipped when import_orders=False                 |
| `test_sync_orders_lookback_days_calculation`         | Verify date range calculation from lookback_days             |
| `test_sync_orders_updates_last_sync_timestamp`       | Verify last_sync_at is updated                               |
| `test_sync_orders_creates_order_bindings`            | Verify amazon.sale.order records created                     |
| `test_sync_orders_handles_pagination`                | Verify NextToken pagination handling                         |
| `test_sync_orders_updates_existing_orders`           | Verify status/field updates on re-sync                       |
| `test_action_push_stock_requires_push_stock_enabled` | Verify feature flag validation                               |
| `test_action_push_stock_enabled`                     | Verify NotImplementedError for unimplemented feature         |
| `test_multiple_shops_same_backend`                   | Verify backend can have multiple shops                       |
| `test_shop_warehouse_defaults_to_backend_warehouse`  | Verify warehouse inheritance                                 |

**Mock Usage:**

- `@mock.patch.object("amazon.backend", "_call_sp_api")` - Mock SP-API calls
- Tests pagination, error handling, and field updates

### 4. **test_order.py** - Order Model Tests (16 tests)

Tests for `amazon.sale.order` and `amazon.sale.order.line` models covering order import
and synchronization.

**Test Coverage:**

| Test                                          | Purpose                                      |
| --------------------------------------------- | -------------------------------------------- |
| `test_order_creation`                         | Verify order record creation                 |
| `test_create_order_from_amazon_data`          | Verify order creation from API data          |
| `test_create_order_updates_existing`          | Verify existing orders are updated           |
| `test_create_order_updates_last_update_date`  | Verify timestamp updates                     |
| `test_sync_order_lines_fetches_from_api`      | Mock order items endpoint                    |
| `test_create_order_line_from_amazon_data`     | Verify line creation from API data           |
| `test_create_order_line_finds_product_by_sku` | Verify product matching by SKU               |
| `test_create_order_line_without_product`      | Verify graceful handling of missing products |
| `test_order_line_quantity_and_pricing`        | Verify numerical field accuracy              |
| `test_sync_order_lines_pagination`            | Verify NextToken pagination for lines        |
| `test_order_line_creation_with_all_fields`    | Verify all Amazon fields are stored          |
| `test_order_with_no_lines_no_sync_error`      | Verify empty order handling                  |
| `test_order_fields_match_amazon_order_data`   | Verify field mapping accuracy                |
| Additional tests                              | Error handling, edge cases, data validation  |

**Mock Usage:**

- `@mock.patch.object("amazon.backend", "_call_sp_api")` - Mock order items endpoint
- Tests product matching, pagination, and field mapping

## Running the Tests

### Run All Tests

```bash
cd /path/to/connector_amazon_spapi
python -m pytest tests/
```

### Run Specific Test File

```bash
python -m pytest tests/test_backend.py -v
python -m pytest tests/test_shop.py -v
python -m pytest tests/test_order.py -v
```

### Run Specific Test Method

```bash
python -m pytest tests/test_backend.py::TestAmazonBackend::test_backend_creation -v
```

### Run with Coverage Report

```bash
python -m pytest tests/ --cov=. --cov-report=html
```

### Run via Odoo Test Suite

```bash
odoo --test-enable -d test_db -i connector_amazon_spapi
```

## Test Data and Fixtures

### Backend Fixture

```python
{
    'name': 'Test Amazon Backend',
    'code': 'test_amazon',
    'version': 'spapi',
    'seller_id': 'AKIAIOSFODNN7EXAMPLE',
    'region': 'na',
    'lwa_client_id': 'amzn1.application-oa2-client.example',
    'lwa_client_secret': 'test-client-secret-1234567890'
}
```

### Marketplace Fixture

```python
{
    'name': 'Amazon.com',
    'marketplace_id': 'ATVPDKIKX0DER',
    'region': 'NA',
    'backend_id': backend.id
}
```

### Shop Fixture

```python
{
    'name': 'Test Amazon Shop',
    'backend_id': backend.id,
    'marketplace_id': marketplace.id,
    'import_orders': True,
    'push_stock': False,
    'lookback_days': 30
}
```

### Sample Amazon Order Data

```python
{
    'AmazonOrderId': '111-1111111-1111111',
    'PurchaseDate': '2025-01-15T10:30:00Z',
    'OrderStatus': 'Pending',
    'FulfillmentChannel': 'MFN',
    'ShippingAddress': {
        'Name': 'John Doe',
        'AddressLine1': '123 Main St',
        'City': 'New York',
        'StateOrRegion': 'NY',
        'PostalCode': '10001',
        'CountryCode': 'US'
    },
    'BuyerEmail': 'buyer@example.com',
    'OrderTotal': {
        'Amount': '149.99',
        'CurrencyCode': 'USD'
    }
}
```

## OCA Best Practices Followed

✅ **Test Organization**

- Base class with shared fixtures in `common.py`
- Separate test files by model/feature
- Clear, descriptive test method names

✅ **Test Isolation**

- Each test runs in isolated transaction (TransactionCase)
- No test interdependencies
- Automatic rollback after each test

✅ **Mock External Dependencies**

- Requests library mocked with `@mock.patch`
- External API calls never actually made
- Deterministic test behavior

✅ **Realistic Test Data**

- Sample data matches actual Amazon SP-API response structure
- Includes edge cases and validation scenarios
- Helper methods for common fixtures

✅ **Documentation**

- Clear docstrings for each test
- Comments explaining complex assertions
- README with full test documentation

✅ **Coverage**

- Multiple test scenarios per feature
- Success and failure paths tested
- Edge cases and error handling

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

- No external dependencies required (all mocked)
- Fast execution (~5-10 seconds for full suite)
- Clear pass/fail output
- Coverage reporting support

## Extending the Tests

To add new tests:

1. **For backend functionality**: Add to `TestAmazonBackend` class in `test_backend.py`
2. **For shop operations**: Add to `TestAmazonShop` class in `test_shop.py`
3. **For order operations**: Add to `TestAmazonOrder` class in `test_order.py`
4. **For new fixtures**: Add helper method to `CommonConnectorAmazonSpapi` in
   `common.py`

Example:

```python
def test_new_feature(self):
    """Test description"""
    # Setup
    test_data = self._create_backend(region="eu")

    # Execute
    result = test_data.some_method()

    # Assert
    self.assertEqual(result, expected_value)
```

## Troubleshooting

### Mock Not Working

- Ensure path is correct: `@mock.patch("requests.post")`
- Patch at import location, not original module

### Test Order Dependency

- Each test is independent; no test should depend on another
- All fixtures created fresh in `setUp()` method

### Token Expiry Issues

- Use `datetime.now() + timedelta(hours=1)` for future tokens
- Use `datetime.now() - timedelta(hours=1)` for expired tokens

### Database State

- Never commit changes in tests
- Use `self.env[model].create()` for test records
- All changes automatically rolled back after test

## Related Documentation

- [Amazon SP-API Documentation](https://developer.amazon.com/docs/amazon-selling-partner-apis/sp-api-overview.html)
- [Odoo Testing Documentation](https://www.odoo.com/documentation/16.0/developer/reference/backend/testing.html)
- [OCA Testing Patterns](https://github.com/OCA/maintainer-tools/wiki/Coding-guidelines)
