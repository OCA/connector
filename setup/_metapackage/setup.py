import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-component',
        'odoo12-addon-test_component',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
