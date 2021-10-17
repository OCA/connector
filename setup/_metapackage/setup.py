import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-component',
        'odoo10-addon-component_event',
        'odoo10-addon-connector',
        'odoo10-addon-connector_base_product',
        'odoo10-addon-test_component',
        'odoo10-addon-test_connector',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 10.0',
    ]
)
