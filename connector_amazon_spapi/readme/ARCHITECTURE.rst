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
