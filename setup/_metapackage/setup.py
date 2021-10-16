import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-component',
        'odoo13-addon-component_event',
        'odoo13-addon-connector',
        'odoo13-addon-connector_base_product',
        'odoo13-addon-test_component',
        'odoo13-addon-test_connector',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 13.0',
    ]
)
