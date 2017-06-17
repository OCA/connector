.. _code-overview:

#############
Code Overview
#############

Here is an overview of some of the concepts in the framework.

As an example, we'll see the steps for exporting an invoice to Magento.
The steps won't show all the steps, but a simplified excerpt of a real
use case exposing the main ideas.

*************
Backend Model
*************

All start with the declaration of the Backend.

.. code-block:: python

    class MagentoBackend(models.Model):
        _name = 'magento.backend'
        _description = 'Magento Backend'
        _inherit = 'connector.backend'

        location = fields.Char(string='Location')
        username = fields.Char(string='Username')
        password = fields.Char(string='Password')

In the Components dialect, we'll call it a Collection.


********
Bindings
********

The ``binding`` is the link between an Odoo record and an external
record. There is no forced implementation for the ``bindings``.

Usually, a binding model that ``_inherits`` the record to synchronize is
created, in which we will store the id of the Backend, the id of the record
and the external id.

You might also store the external id in the same model, but you would not be
able to synchronize the same record with several backends (several instances
of Magento for instance).

In a real case, some of the fields below and the export_record method are
inherited from an abstract binding.  But for clarity, all the required fields
are shown

.. code-block:: python

    class MagentoAccountInvoice(models.Model):
        _name = 'magento.account.invoice'
        _inherits = {'account.invoice': 'odoo_id'}
        _description = 'Magento Invoice'

        backend_id = fields.Many2one(comodel_name='magento.backend', string='Magento Backend', required=True, ondelete='restrict')
        odoo_id = fields.Many2one(comodel_name='account.invoice', string='Invoice', required=True, ondelete='cascade')
        magento_id = fields.Char(string='ID on Magento')  # fields.char because 0 is a valid Magento ID
        sync_date = fields.Datetime(string='Last synchronization date')
        magento_order_id = fields.Many2one(comodel_name='magento.sale.order', string='Magento Sale Order', ondelete='set null')
        # we can also store additional data related to the Magento Invoice

        @job
        @api.multi
        def export_record(self):
            """ Export a validated or paid invoice. """
            self.ensure_one()
            work = self.backend_id.work_on(self._name)
            invoice_exporter = work.component(usage='record.exporter')
            return invoice_exporter.run(self)


The decorator ``@job`` means this method can be delayed in the jobs queue, so
instead of being executed synchronously, it will be executed by a different
worker as soon as possible.

In the ``export_record`` job, you can have a first glance at the components
system.


******
Events
******

We can create :py:class:`~connector.event.Event` on which we'll be able
to subscribe consumers.  The connector already integrates the most
generic ones:
:py:meth:`~connector.event.on_record_create`,
:py:meth:`~connector.event.on_record_write`,
:py:meth:`~connector.event.on_record_unlink`

When we create a ``magento.account.invoice`` record, we want to delay a
job to export it to Magento, so we subscribe a new consumer on
:py:meth:`~connector.event.on_record_create`:

.. code-block:: python

  @on_record_create(model_names='magento.account.invoice')
  def delay_export_account_invoice(env, model_name, record_id):
      """ Delay the job to export the magento invoice.  """
      env[model_name].browse(record_id).with_delay().export_invoice()

When a ``magento.account.invoice`` is created, the event will be triggered,
calling ``delay_export_account_invoice`` in turn.  There is a lot of things
happening on the last line., we'll see that in the `Jobs`_ section.

****
Jobs
****

A :py:class:`~connector.queue.job.Job` is a task to execute later.
In that case: create the invoice on Magento.

Any Model method decorated with :meth:`~odoo.addons.queue_job.job.job` can be
posted in the queue of jobs.  Calling
:meth:`~odoo.addons.queue_job.models.base.Base.with_delay` on a record or
model returns a delayable version of the record/model. Any call on it will
delay the called method instead of executing it (if the method is decorated by
``@job``).

.. code-block:: python

    @job
    @api.multi
    def export_record(self):
        """ Export a validated or paid invoice. """
        self.ensure_one()
        work = self.backend_id.work_on(self._name)
        invoice_exporter = work.component(usage='record.exporter')
        return invoice_exporter.run(self)


The job above is invoked with:

.. code-block:: python

    delayable = record.with_delay(priority=10)
    delayable.export_record()

Notes on the jobs:

* The content of the method will be executed only when the Jobrunner takes it
* ``self`` will be the record on which we delayed the job originally
* The same method could have been invoked in a synchronous way with
  ``record.export_record()``
* ``with_delay()`` takes arguments for the job, like a priority or an ETA
* if we had arguments passed to ``export_record``, they would have been passed
  along when the job is executed

Some explanations on what happens inside the job:

* We are working on a binding record (``magento.account.invoice``).
  It has a link to the Backend (``backend_id``).
* From this backend, we obtain a
  :class:`~odoo.addons.component.core.WorkContext`, which will be passed along
  transversally in all the components we might use.  It indicates we are
  working with the ``magento.account.invoice`` model.  *
  :meth:`~odoo.addons.component.core.WorkContext.component` gives us a
  component for the current collection, current model and the usage we ask it.
  More details on the usage in `Components`_.


**********
Components
**********

Components are organized according to different usages.  The connector
suggests 5 main kinds of Components. Each might have a few different usages.
You can be as creative as you want when it comes to creating new ones though.

One "usage" is responsible for a specific work, and alongside with the
collection (the backend) and the model, the usage will be used to find the
needed component for a task.

Some of the Components have an implementation in the ``Connector`` addon, but
some are empty shells that need to be implemented in the different connectors.

The usual categories are:

:py:class:`~connector.components.binder.Binder`
  The ``binders`` give the external ID or Odoo ID from respectively an
  Odoo ID or an external ID. A default implementation is available.

  Most common usages:

  * ``binder``

:py:class:`~connector.components.mapper.Mapper`
  The ``mappers`` transform a external record into an Odoo record or
  conversely.

  Most common usages:

  * ``import.mapper``
  * ``export.mapper``

:py:class:`~connector.components.backend_adapter.BackendAdapter`
  The ``backend.adapters`` implements the discussion with the ``backend's``
  APIs. They usually adapt their APIs to a common interface (CRUD).

  Most common usages:

  * ``backend.adapter``

:py:class:`~connector.components.synchronizer.Synchronizer`
  A ``synchronizer`` is the main piece of a synchronization.  It
  orchestrates the flow of a synchronization and use the other
  Components

  Most common usages:

  * ``record.importer``
  * ``record.exporter``
  * ``batch.importer``
  * ``batch.exporter``

For the export of the invoice, we need a ``backend.adapter`` and a
``synchronizer`` (the real implementation is more complete):

.. code-block:: python

    class AccountInvoiceAdapter(Component):
        """ Backend Adapter for the Magento Invoice """
        # used for inheritance
        _name = 'magento.invoice.adapter'
        _inherit = 'magento.adapter'

        # used for the lookup of the component
        _apply_on = 'magento.account.invoice'
        _usage = 'backend.adapter'

        # name of the method in the Magento API
        _magento_model = 'sales_order_invoice'

        def create(self, order_increment_id, items, comment, email, include_comment):
            """ Create a record on the external system """
            return self._call('%s.create' % self._magento_model,
                              [order_increment_id, items, comment,
                              email, include_comment])

    class MagentoInvoiceExporter(Component):
        """ Export invoices to Magento """
        # used for inheritance
        _name = 'magento.invoice.exporter'
        _inherit = 'magento.exporter'

        # used for the lookup of the component
        # you can see this is what was used in
        # work.component(usage='record.exporter')
        _apply_on = 'magento.account.invoice'
        _usage = 'record.exporter'

        def _get_lines_info(self, binding):
            # [...]

        def run(self, binding):
            """ Run the job to export the validated/paid invoice """
            # get the binder for the sale, we need the Magento ID of it
            sale_binder = self.component(
                usage='binder',
                model_name='magento.sale.order'
            )
            magento_order = binding.magento_order_id
            # get the external ID of the sale order
            sale_external_id = sale_binder.to_external(magento_order)

            lines_info = self._get_lines_info(binding)

            # find the Backend Adapter and create the invoice
            backend_adapter = self.component(usage='backend.adapter')
            backend_adapter.create(
                sale_external_id, lines_info,
                _("Invoice Created"),
                mail_notification,
                False,
            )

            # use the binder for this model to store the external ID in our
            # binding
            binder = self.component(usage='binder')
            binder.bind(magento_id, binding)
