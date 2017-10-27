import setuptools

setuptools.setup(
    install_requires=['cachetools>=2.0.1'],
    setup_requires=['setuptools-odoo'],
    odoo_addon=True,
)
