.. _bootstrap-connector:


########################
Boostrapping a connector
########################

We'll see the steps to bootstrap a new connector.

Besides that, you may want to use the existing connectors to have some
real implementation examples:

* `OpenERP Magento Connector`_
* `OpenERP Prestashop Connector`_

Some boilerplate is necessary, so this document will guide you through
some steps. Please also take a look on the :ref:`naming-convention`.

For the sake of the example, we'll imagine we have to synchronize
OpenERP with a coffee machine.

****************
OpenERP Manifest
****************

As we want to synchronize OpenERP with a coffee machine, we'll name
our connector connector_coffee.

First, we need to create the OpenERP addons itself, editing the
``connector_coffee/__openerp__.py`` manifest.


.. code-block:: python
   :emphasize-lines: 4,5

    # -*- coding: utf-8 -*-
    {'name': 'Coffee Connector',
     'version': '1.0.0',
     'category': 'Connector',
     'depends': ['connector',
                 ],
     'author': 'Myself',
     'license': 'AGPL-3',
     'description': """
    Coffee Connector
    ================

    Connect OpenERP to my coffee machine.

    Features:

    * Poor a coffee when OpenERP is busy for too long
    """,
     'data': [],
     'installable': True,
     'application': False,
    }

Nothing special but 2 things to note:

* It depends from ``connector``.
* The module category should be ``Connector``.

Of course, we also need to create the ``__init__.py`` file where we will
put the imports of our python modules.


***********************************
Install the module in the connector
***********************************

Each new module needs to be plugged in the connector's framework.
That's just a matter of following a convention and creating
``connector_coffee/connector.py`` in which you will call the
``install_in_connector`` function::

    from openerp.addons.connector.connector import install_in_connector


    install_in_connector()

.. warning:: If you miss this line of code, your ConnectorUnit classes won't
             be found.

.. note:: The reason for this is that OpenERP may import the Python modules
          of uninstalled modules, so it automatically registers the
          events and ConnectorUnit classes, even for uninstalled
          modules.

          To prevent this, we use a little trick: create an abstract
          model and look in the registry if it is loaded.


********************
Declare the backends
********************

Our module is compatible with the coffee machines:

 * Coffee 1900
 * Coffee 2900

So we'll declare a backend `coffee`, the generic entity,
and a backend per version.

Put this in ``connector_coffee/backend.py``::

    import openerp.addons.connector.backend as backend


    coffee = backend.Backend('coffee')
    coffee1900 = backend.Backend(parent=coffee, version='1900')
    coffee2900 = backend.Backend(parent=coffee, version='2900')


*************
Backend Model
*************

We declared the backends, but we need a model to configure them.

We create a model ``coffee.backend`` which is an ``_inherit`` of
``connector.backend``. In ``connector_coffee/coffee_model.py``::

    from openerp.osv import fields, orm


    class coffee_backend(orm.Model):
        _name = 'coffee.backend'
        _description = 'Coffee Backend'
        _inherit = 'connector.backend'

        _backend_type = 'coffee'

        def _select_versions(self, cr, uid, context=None):
            """ Available versions

            Can be inherited to add custom versions.
            """
            return [('1900', '2900')]

        _columns = {
            'version': fields.selection(
                _select_versions,
                string='Version',
                required=True),
            'location': fields.char('Location'),
            'username': fields.char('Username'),
            'password': fields.char('Password'),
            'default_lang_id': fields.many2one(
                'res.lang',
                'Default Language'),
        }

Notes:

* The ``_backend_type`` must be the same than the name in the backend in
  `Declare the backends`_.
* the versions should be the same than the ones declared in `Declare the backends`_.
* We may want to add as many fields as we want to configure our
  connection or configuration regarding the backend in that model.


****************
Abstract Binding
****************

If we have many :ref:`binding`,
we may want to create an abstract model for them.

It can be as follows (in ``connector_coffee/connector.py``)::

    from openerp.osv import orm, fields


    class coffee_binding(orm.AbstractModel):
        _name = 'coffee.binding'
        _inherit = 'external.binding'
        _description = 'Coffee Binding (abstract)'

        _columns = {
            # 'openerp_id': openerp-side id must be declared in concrete model
            'backend_id': fields.many2one(
                'coffee.backend',
                'Coffee Backend',
                required=True,
                ondelete='restrict'),
            # fields.char because 0 is a valid coffee ID
            'coffee_id': fields.char('ID in the Coffee Machine',
                                     select=True),
        }


***********
Environment
***********

We'll often need to create a new environment to work with.
I propose to create a helper method which build it for us (in
``connector_coffee/connector.py``::

    from openerp.addons.connector.connector import Environment


    def get_environment(session, model_name, backend_id):
        """ Create an environment to work with. """
        backend_record = session.browse('coffee.backend', backend_id)
        env = Environment(backend_record, session, model_name)
        lang = backend_record.default_lang_id
        lang_code = lang.code if lang else 'en_US'
        env.set_lang(code=lang_code)
        return env

Note that the part regarding the language definition is totally
optional but I left it as an example.


***********
Checkpoints
***********

When new records are imported and need a review, :ref:`checkpoint` are
created. I propose to create a helper too in
``connector_coffee/connector.py``::

    from openerp.addons.connector.checkpoint import checkpoint


    def add_checkpoint(session, model_name, record_id, backend_id):
        return checkpoint.add_checkpoint(session, model_name, record_id,
                                         'coffee.backend', backend_id)

*********************
ConnectorUnit classes
*********************

We'll probably need to create synchronizers, mappers, backend adapters,
binders and maybe our own types of ConnectorUnit classes.

Their implementation can vary a lot. Have a look on the
`OpenERP Magento Connector`_ and `OpenERP Prestashop Connector`_ projects.


.. _`OpenERP Magento Connector`: https://code.launchpad.net/openerp-connector-magento
.. _`OpenERP Prestashop Connector`: https://code.launchpad.net/prestashoperpconnect
