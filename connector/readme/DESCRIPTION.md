This is a framework designed to build connectors with external systems,
usually called `Backends` in the documentation.

Documentation: <http://odoo-connector.com>

It features:

- A jobs queue

  > In which the connectors can push functions (synchronization tasks)
  > to be executed later.

- An event pattern

  > The connectors can subscribe listener functions on the events,
  > executed when the events are fired.

- Connector base classes

  > Called `ConnectorUnit`.
  >
  > Include base classes for the use in connectors, ready to be
  > extended:
  >
  > - `Synchronizer`: flow of an import or export
  > - `Mapper`: transform a record according to mapping rules
  > - `Binder`: link external IDs with local IDS
  > - `BackendAdapter`: adapter interface for the exchanges with the
  >   backend
  > - But `ConnectorUnit` can be extended to accomplish any task

- A multi-backend support

  > Each `ConnectorUnit` can be registered amongst a backend type (eg.
  > Magento) and a backend version (allow to have a different `Mapper`
  > for each backend's version for instance)

It is used for example used to connect
[Magento](http://odoo-magento-connector.com) and
[Prestashop](https://github.com/OCA/connector-prestashop), but also used
with Solr, CMIS, ...
