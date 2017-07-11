.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==========
Components
==========

This module implements a component system and is a base block for the Connector
Framework. It can be used without using the full Connector though.

Documentation: http://odoo-connector.com/

Installation
============

* Install ``component``

Configuration
=============

The module does nothing by itself and has no configuration.

Usage
=====

As a developer, you have access to a component system. You can find the
documentation in the code or on http://odoo-connector.com

In a nutshell, you can create components::


  from odoo.addons.component.core import Component

  class MagentoPartnerAdapter(Component):
      _name = 'magento.partner.adapter'
      _inherit = 'magento.adapter'

      _usage = 'backend.adapter'
      _collection = 'magento.backend'
      _apply_on = ['res.partner']

And later, find the component you need at runtime (dynamic dispatch at
component level)::

  def run(self, external_id):
      backend_adapter = self.component(usage='backend.adapter')
      external_data = backend_adapter.read(external_id)


Known issues / Roadmap
======================

* ...

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
