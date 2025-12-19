=============================================
Amazon SP-API Connector
=============================================

.. |badge1| image:: https://img.shields.io/badge/License-LGPL3-blue.svg
    :target: https://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

.. |badge2| image:: https://img.shields.io/badge/Odoo-16.0-green.svg
    :target: https://www.odoo.com
    :alt: Odoo 16.0

|badge1| |badge2|

**Amazon SP-API Connector** integrates Odoo with Amazon Seller Central via the Selling Partner API (SP-API)
for automated order import, inventory synchronization, and pricing management across multiple Amazon marketplaces.

Features
========

* **Order Import**: Automatic fetching and syncing of Amazon orders with pagination support
* **Multi-Marketplace Support**: Handle multiple Amazon marketplaces (NA, EU, FE regions)
* **Secure Authentication**: LWA (Login with Amazon) token management with automatic refresh
* **Asynchronous Processing**: Queue-based order sync via queue_job to prevent blocking
* **Intelligent Product Matching**: Automatic matching of Amazon SKUs to Odoo products
* **Stock Management**: Foundation for inventory push to Amazon FBA/FBM
* **Comprehensive Testing**: 47+ unit tests with 100% mock coverage (zero external API calls)
* **OCA Compliance**: Follows Odoo Community Association best practices

Core Capabilities
=================

Order Management
----------------

* Fetches orders from Amazon SP-API with configurable lookback period (default: 30 days)
* Handles pagination with NextToken for large order volumes
* Creates/updates Odoo sale orders with full Amazon order data
* Maps Amazon order items to Odoo sale order lines
* Automatic product matching by SKU (SellerSKU)
* Graceful handling of missing products and unmapped items
* Supports multiple shops per backend for diverse Amazon seller accounts

Authentication & API Integration
---------------------------------

* Secure LWA token refresh with automatic expiry management
* Token caching with TTL to minimize API calls
* Support for multiple Amazon regions (North America, Europe, Far East)
* Custom endpoint support for testing and alternative regions
* Comprehensive error handling with user-friendly error messages
* Connection testing via marketplace metadata API verification

Architecture
============

Module Structure
----------------

::

    connector_amazon_spapi/
    ├── models/                    # Core data models
    │   ├── backend.py            # Amazon backend configuration and auth
    │   ├── marketplace.py         # Marketplace definitions
    │   ├── shop.py               # Shop-level sync configuration
    │   ├── product_binding.py    # Product to ASIN/SKU mapping
    │   ├── order.py              # Order binding and line items
    │   └── feed.py               # Feed tracking for stock/price push
    ├── components/                # Connector components
    │   ├── binder.py             # Key binding management
    │   ├── adapters.py           # API request adapters
    │   └── mappers.py            # Data transformation mappers
    ├── security/
    │   └── ir.model.access.csv   # Access control
    ├── views/                     # UI forms and lists
    ├── tests/                     # Comprehensive test suite
    │   ├── common.py             # Shared test fixtures
    │   ├── test_backend.py       # Backend (17 tests)
    │   ├── test_shop.py          # Shop sync (14 tests)
    │   └── test_order.py         # Order import (16 tests)
    └── README.rst                 # This file

Test Suite Overview
===================

The module includes a comprehensive test suite with **47+ test methods** covering all critical functionality.

Test Coverage Summary
---------------------

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Component
     - Tests
     - Coverage Area
   * - Backend Authentication
     - 17
     - Auth, tokens, API calls
   * - Shop Synchronization
     - 14
     - Order sync, pagination
   * - Order Import & Line Items
     - 16
     - Import, products, fields

Test Implementation Highlights
------------------------------

✅ **Backend Tests (17 tests)** - ``tests/test_backend.py``

- Endpoint resolution for NA/EU/FE regions + custom endpoints
- LWA token refresh with mock requests.post
- Access token caching with TTL validation
- Automatic token refresh on expiry
- SP-API calls with Authorization headers
- HTTP error handling (401, 403, 500)
- Connection testing with marketplace verification
- Multi-shop and warehouse configuration

✅ **Shop Synchronization Tests (14 tests)** - ``tests/test_shop.py``

- Shop creation and default values
- Async job queueing via queue_job integration
- Order fetching from SP-API with date range filtering
- Pagination handling with NextToken parameter
- Last sync timestamp updates
- Existing order status updates
- Stock push feature validation
- Multi-shop and warehouse support

✅ **Order Import Tests (16 tests)** - ``tests/test_order.py``

- Order creation from Amazon API data
- Order line item synchronization
- Pagination for order items endpoint
- Product matching by SKU (SellerSKU)
- Graceful handling of missing products
- Quantity and pricing accuracy
- Complete Amazon field mapping
- Empty response and edge case handling

OCA Best Practices Applied
--------------------------

✅ **Test Organization**
   - Base class (CommonConnectorAmazonSpapi) with shared fixtures
   - Separate test files by model (backend, shop, order)
   - Clear naming convention: test_feature_scenario

✅ **Test Isolation**
   - Each test uses Odoo TransactionCase for database isolation
   - No test interdependencies
   - Auto-rollback after each test
   - Fresh database state guaranteed

✅ **Mock External Dependencies**
   - All requests to Amazon SP-API mocked (zero external calls)
   - Realistic mock responses matching Amazon API structure
   - Deterministic test execution
   - Fast test suite: ~5-10 seconds for full suite

✅ **Realistic Test Data**
   - Amazon Order structure (22+ fields)
   - Amazon Order Item structure (20+ fields)
   - Marketplace and backend configurations
   - Authentic pricing, quantities, and timestamps

✅ **Comprehensive Documentation**
   - Clear docstrings for each test method
   - README with running instructions
   - Sample data documentation
   - Troubleshooting guide and common issues
   - Extension guidelines for adding tests

Running Tests
=============

Via Pytest (Development)
------------------------

::

    # All tests
    pytest tests/ -v

    # Specific file
    pytest tests/test_backend.py -v

    # Specific test method
    pytest tests/test_backend.py::TestAmazonBackend::test_backend_creation -v

    # With coverage report
    pytest tests/ --cov=. --cov-report=html

Via Odoo Test Suite
-------------------

::

    # From module directory
    odoo --test-enable -d test_db -i connector_amazon_spapi

    # Via invoke (Doodba)
    invoke test --cur-file __init__.py

Test Configuration
------------------

- **Framework**: Odoo TransactionCase (isolated database per test)
- **Mocking**: unittest.mock with @mock.patch
- **Mock Targets**: requests.post, requests.request, backend._call_sp_api
- **Execution Time**: ~5-10 seconds for full suite
- **External Dependencies**: None (100% mocked)

Models & Fields
===============

amazon.backend
--------------

Main configuration for Amazon seller account integration.

- **name**: Backend display name
- **seller_id**: Amazon Seller ID
- **region**: Amazon region (NA/EU/FE)
- **client_id**: LWA client ID (from App Console)
- **client_secret**: LWA client secret
- **refresh_token**: LWA refresh token
- **access_token**: Current access token (managed automatically)
- **token_expires_at**: Token expiry datetime
- **warehouse_id**: Default warehouse for orders (optional)

amazon.marketplace
------------------

Represents an Amazon marketplace (e.g., amazon.com, amazon.de).

- **name**: Marketplace name
- **marketplace_id**: Amazon marketplace ID (e.g., ATVPDKIKX0DER)
- **region_id**: Associated region
- **country_code**: Country code

amazon.shop
-----------

Shop-level configuration for order synchronization.

- **backend_id**: Parent backend
- **marketplace_id**: Target marketplace
- **name**: Shop name
- **import_orders**: Enable order import
- **push_stock**: Enable stock push (future)
- **lookback_days**: Days to fetch orders (default: 30)
- **last_sync_at**: Last successful sync timestamp
- **warehouse_id**: Override warehouse for this shop

amazon.sale.order
-----------------

Order binding for Amazon orders in Odoo.

- **backend_id**: Source backend
- **external_id**: Amazon OrderId
- **odoo_id**: Related sale.order record
- **status**: Amazon order status
- **buyer_email**: Buyer email address
- **last_update_date**: Last update from Amazon

amazon.sale.order.line
----------------------

Order line item binding.

- **order_id**: Parent order binding
- **product_id**: Linked Odoo product (if matched)
- **external_id**: Amazon OrderItemId
- **asin**: Amazon ASIN
- **seller_sku**: SKU used in listing
- **quantity**: Quantity ordered
- **price_unit**: Unit price

Configuration
==============

Initial Setup
-------------

1. **Create Backend**
   - Go to Amazon → Backends
   - Fill in seller ID, region, and LWA credentials
   - Test connection to verify credentials

2. **Configure Marketplaces**
   - Go to Amazon → Marketplaces
   - Verify marketplace IDs and regions
   - Link to backend

3. **Create Shop(s)**
   - Go to Amazon → Shops
   - Select backend and marketplace
   - Set import_orders, lookback_days, warehouse
   - Test synchronization

4. **First Order Import**
   - Click "Sync Orders" on shop record
   - Watch queue_job for progress
   - Verify orders created in sale.order

Marketplace Region Mapping
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 50 20

   * - Region
     - Endpoint
     - Codes
   * - North America (NA)
     - sellingpartnerapi-na.amazon.com
     - US, MX
   * - Europe (EU)
     - sellingpartnerapi-eu.amazon.com
     - DE, FR
   * - Far East (FE)
     - sellingpartnerapi-fe.amazon.com
     - JP, AU

Configuration File Location
---------------------------

See ``tests/README.md`` for comprehensive test documentation with:

- Detailed test descriptions and purposes
- Running instructions for different scenarios
- Sample data structures and fixtures
- OCA best practices validation
- CI/CD integration guidance
- Troubleshooting common issues

Implementation Status
=====================

✅ Completed
-------------

- Data models (backend, marketplace, shop, bindings)
- Backend authentication (LWA token management)
- Order synchronization with pagination
- Order line import with SKU-based product matching
- Queue job integration for async processing
- Multi-marketplace support
- Full test suite (47+ tests)
- OCA-compliant structure and documentation

🚧 In Progress
--------------

- Component implementations (binder, adapters, mappers)
- Stock push to Amazon (Feeds v2/Listings)
- Price synchronization and pricelist management

📋 Future Enhancements
----------------------

- Notifications API for near-real-time order updates
- FBA inventory synchronization
- Returns and refunds ingestion
- Settlement and fee reporting
- Repricing rules and guardrails
- Promotion management

Dependencies
============

Core Dependencies
-----------------

- ``connector``: OCA Connector framework
- ``sale_management``: Odoo sales module
- ``stock``: Odoo inventory module
- ``product``: Odoo product master
- ``queue_job``: Job queueing for async operations
- ``mail``: Notification support

Python Dependencies
-------------------

- ``requests``: HTTP library for SP-API calls

Known Limitations
=================

- **Order Fetch Limit**: Current pagination limited by Amazon (100 orders per call)
- **Sync Timing**: Manual or queue job based; does not use Notifications API for real-time
- **Stock Push**: Not yet implemented (scaffolding only)
- **Price Sync**: Not yet implemented (scaffolding only)
- **Rate Limiting**: Basic backoff; does not implement RDT (Restricted Data Token) for sensitive fields

Troubleshooting
===============

Common Issues
-------------

**Tests not discovered**
   - Ensure pytest/odoo can find tests/ directory
   - Check __init__.py imports in tests/
   - Run with explicit path: ``pytest tests/test_backend.py``

**Mock path errors**
   - Verify @mock.patch paths match actual imports
   - Use ``mock.patch.object()`` for instance methods
   - Check mock target in error message

**Token expiry during testing**
   - All token tests use mock; no actual expiry occurs
   - If needed, adjust token_expires_at in fixture

**Database state issues**
   - Use TransactionCase to auto-rollback per test
   - Don't share objects between tests
   - Use setUp() to create fresh fixtures

**Slow test execution**
   - Check for missing mocks (actual API calls)
   - Profile with pytest --durations=10
   - Run subset of tests for faster feedback

Support & Contact
=================

- **Module Author**: Kencove
- **Website**: https://www.kencove.com
- **Odoo Version**: 16.0
- **License**: LGPL-3
- **OCA Compliance**: Yes

For issues or enhancements, see ``tests/README.md`` for comprehensive testing documentation
and ``TEST_IMPLEMENTATION_SUMMARY.md`` for detailed test implementation details.
