.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Components - Events
===================

This module implements an event system (`Observer pattern`_) and is a
base block for the Connector Framework. It can be used without
using the full Connector though. It is built upon the ``component`` module.

Documentation: http://odoo-connector.com/

.. _Observer pattern: https://en.wikipedia.org/wiki/Observer_pattern

Installation
============

* Install ``component_event``

Configuration
=============

The module does nothing by itself and has no configuration.

Usage
=====

As a developer, you have access to a events system. You can find the
documentation in the code or on http://odoo-connector.com

In a nutshell, you can create trigger events::

  class Base(models.AbstractModel):
      _inherit = 'base'

      @api.model
      def create(self, vals):
          record = super(Base, self).create(vals)
          self._event('on_record_create').notify(record, fields=vals.keys())
          return record

And subscribe listeners to the events::

  from odoo.addons.component.core import Component
  from odoo.addons.component_event import skip_if

  class MagentoListener(Component):
      _name = 'magento.event.listener'
      _inherit = 'base.connector.listener'

      @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
      def on_record_create(self, record, fields=None):
          """ Called when a record is created """
          record.with_delay().export_record(fields=fields)


This module triggers 3 events:

* ``on_record_create(record, fields=None)``
* ``on_record_write(record, fields=None)``
* ``on_record_unlink(record)``


Known issues / Roadmap
======================

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/connector/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Guewen Baconnier <guewen.baconnier@camptocamp.com>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.

