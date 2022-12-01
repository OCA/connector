import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-connector",
    description="Meta package for oca-connector Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-component>=16.0dev,<16.1dev',
        'odoo-addon-test_component>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
