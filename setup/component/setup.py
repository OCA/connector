import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addon=True,
    odoo_addons={
        'external_dependencies_override': {
            'python': {
                'cachetools': 'cachetools>=2.0.1',
            }
        }
    }
)
