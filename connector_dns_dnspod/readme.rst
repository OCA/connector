.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

Connector Dns Dnspod
=====================

This module aims to allows you to manage your DNSPod domain through Odoo.

Installation
============

To install this module, you need to:

 * have basic modules installed (connector_dns)

Configuration
=============

To configure this module, you need to:

 * No specific configuration needed.

Usage
=====

To use this module, you need to:
1.Create a backend which links to your dnspod.cn.
2.When you create a domain belongs to the backend,if the domain 
  export to the dnspod.cn successfully,the state will change to 
  done,else exception.
3.Record can be created only in the domain which state is done. 


For further information, please visit:

 * https://www.odoo.com/forum/help-1

Known issues / Roadmap
======================


Credits
=======


Contributors
------------

* Liu Lixia <liu.lixia@elico-corp.com>
* Augustin Cisterne-Kaas

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization
    whose mission is to support the collaborative development of Odoo features
        and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org. 