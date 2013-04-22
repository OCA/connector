.. _bootstrap-connector:


########################
Boostrapping a connector
########################

We'll see the steps to bootstrap a new connector.

Besides that, you may want to use the existing connectors to have some
real implementation examples:

* Magentoerpconnect_
* Prestashoperpconnect_

Some boilerplate is necessary, so this document will guide you through
some steps.

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


*********************
Consumers boilerplate
*********************

We'll want to register consumers on the
:py:class:`~connector.event.Event`,
OpenERP imports all the python modules even when the addons are not installed.
This is a problem for the consumers as they should be registered only if
the addon is installed.

To prevent this, we use a little trick: create an abstract model and
look in the registry if it is loaded.

So let's create the abstract model in
``connector_coffee/connector.py``::

    from openerp.osv import orm, fields


    class connector_coffee_installed(orm.AbstractModel):
        """Empty model used to know if the module is installed on the
        database.

        If the model is in the registry, the module is installed.
        """
        _name = 'connector_coffee.installed'


And create a decorator to filter the consumers::


    from functools import wraps


    def coffee_consumer(func):
        """ Use this decorator on all the consumers of connector_coffee.

        It will prevent the consumers from being fired when connector_coffee
        addon is not installed.
        """
        @wraps(func)
        def wrapped(*args, **kwargs):
            session = args[0]
            if session.pool.get('connector_coffee.installed'):
                return func(*args, **kwargs)

        return wrapped


Now, when we'll want to subscribe our own consumer on an event, we'll
write for instance::


    @on_record_create(model_names=['res.partner'])
    @coffee_consumer
    def my_consumer(session, model_name, record_id, fields=None):
        print 'partner created'


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
            'coffee_id': fields.char('ID in the Coffee Machine'),
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
Magentoerpconnect_ and Prestashoperpconnect_ projects.


.. _Magentoerpconnect: https://code.launchpad.net/~openerp-connector-core-editors/openerp-connector/7.0-magentoerpconnect
.. _Prestashoperpconnect: 
