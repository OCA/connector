import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-component',
        'odoo14-addon-component_event',
        'odoo14-addon-connector',
        'odoo14-addon-connector_base_product',
        'odoo14-addon-test_component',
        'odoo14-addon-test_connector',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
