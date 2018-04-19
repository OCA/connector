import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-connector',
        'odoo9-addon-connector_base_product',
        'odoo9-addon-connector_job_subscribe',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
