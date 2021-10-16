import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-component',
        'odoo11-addon-component_event',
        'odoo11-addon-connector',
        'odoo11-addon-connector_base_product',
        'odoo11-addon-test_component',
        'odoo11-addon-test_connector',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 11.0',
    ]
)
