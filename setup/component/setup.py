import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addons={
        'external_dependencies_override': {
            'python': {
                'cachetools': 'cachetools>=2.0.1,<3.0.0',
            }
        }
    }
)
