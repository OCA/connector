# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# Copyright 2017 Odoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from collections import defaultdict, OrderedDict

from odoo.tools import OrderedSet, LastOrderedSet
from ..connector import _get_addon_name


class ComponentGlobalRegistry(OrderedDict):
    """ Store all the components by name

    Allow to _inherit components.

    Another registry allow to register components on a
    particular backend and to find them back.

    This is an OrderedDict, because we want to keep the
    registration order of the components, addons loaded first
    have their components found first (when we look for a list
    components using `multi`).

    """

all_components = ComponentGlobalRegistry()


class WorkContext(object):

    def __init__(self, collection, model_name, **kwargs):
        self.collection = collection
        self.model_name = model_name
        self.model = self.env[model_name]
        self._propagate_kwargs = []
        for attr_name, value in kwargs.iteritems:
            setattr(self, attr_name, value)
            self._propagate_kwargs.append(attr_name)

    @property
    def env(self):
        return self.collection.env

    def work_on(self, model_name):
        kwargs = {attr_name: getattr(self, attr_name)
                  for attr_name in self._propagate_kwargs}
        return self.__class__(self.collection, model_name, **kwargs)

    def components(self, name=None, usage=None, model_name=None, multi=False):
        all_components['base'](self).components(
            name=name,
            usage=usage,
            model_name=model_name,
            multi=multi,
        )

    def __str__(self):
        return "WorkContext(%s,%s)" % (repr(self.collection), self.model_name)

    def __unicode__(self):
        return unicode(str(self))

    __repr__ = __str__


class MetaComponent(type):

    _modules_components = defaultdict(list)

    def __init__(self, name, bases, attrs):
        if not self._register:
            self._register = True
            super(MetaComponent, self).__init__(name, bases, attrs)
            return

        if not hasattr(self, '_module'):
            self._module = _get_addon_name(self.__module__)

        self._modules_components[self._module].append(self)


class Component(object):
    __metaclass__ = MetaComponent

    _register = False

    _name = None
    _inherit = None

    # name of the collection to subscribe in, abstract when None
    _collection = None

    _apply_on = None  # None means any Model, can be a list ['res.users', ...]
    _usage = None  # component purpose, might be a list? ['import.mapper', ...]

    def __init__(self, work_context):
        super(Component, self).__init__()
        self.work = work_context

    @property
    def apply_on_models(self):
        # None means all models
        if self._apply_on is None:
            return None
        # always return a list, used for the lookup
        elif isinstance(self._apply_on, basestring):
            return [self._apply_on]
        return self._apply_on

    @property
    def collection(self):
        return self.work.collection

    @property
    def env(self):
        return self.collection.env

    @property
    def model(self):
        return self.collection.model

    # TODO use a LRU cache (repoze.lru, beware we must include the collection
    # name in the cache but not 'self')
    @staticmethod  # staticmethod in order to use a LRU cache on all args
    def lookup(collection_name, name=None, usage=None, model_name=None,
               multi=False):
        # keep the order so addons loaded first have components used first
        # in case of multi=True
        candidates = OrderedSet()
        if name is not None:
            component = all_components.get(name)
            if not component:
                # TODO: which error type?
                raise ValueError("No component with name '%s' found." % name)
            candidates.add(component)

        if usage is not None:
            components = [c for c in all_components.itervalues()
                          if c._usage == usage]
            if components:
                candidates.update(components)

        if name is None and usage is None:
            candidates.update(all_components.values())

        # filter out by model name
        candidates = OrderedSet(c for c in candidates
                                if c.apply_on_models is None
                                or model_name in c.apply_on_models)

        if not multi and len(candidates) > 1:
            # TODO which error type?
            raise ValueError(
                "Several components found for collection '%s', name '%s', "
                "usage '%s', model_name '%s'. Found: %s" %
                (collection_name, name, usage, model_name, candidates)
            )

        return candidates

    def components(self, name=None, usage=None, model_name=None, multi=False):
        return self.lookup(
            self.collection._name,
            name=name,
            usage=usage,
            model_name=model_name,
            multi=multi,
        )(self.work)

    def __str__(self):
        return "Component(%s)" % self._name

    def __unicode__(self):
        return unicode(str(self))

    __repr__ = __str__

    #
    # Goal: try to apply inheritance at the instantiation level and
    #       put objects in the registry var
    #
    @classmethod
    def _build_component(cls, registry):
        """ Instantiate a given Component in the registry.

        This method creates or extends a "registry" class for the given
        component.
        This "registry" class carries inferred component metadata, and inherits
        (in the Python sense) from all classes that define the component, and
        possibly other registry classes.

        """

        # In the simplest case, the component's registry class inherits from
        # cls and the other classes that define the component in a flat
        # hierarchy.  The registry contains the instance ``component`` (on the
        # left). Its class, ``ComponentClass``, carries inferred metadata that
        # is shared between all the component's instances for this registry
        # only.
        #
        #   class A1(Component):                    Component
        #       _name = 'a'                           / | \
        #                                            A3 A2 A1
        #   class A2(Component):                      \ | /
        #       _inherit = 'a'                    ComponentClass
        #
        #   class A3(Component):
        #       _inherit = 'a'
        #
        # When a component is extended by '_inherit', its base classes are modified
        # to include the current class and the other inherited component classes.
        # Note that we actually inherit from other ``ComponentClass``, so that
        # extensions to an inherited component are immediately visible in the
        # current component class, like in the following example:
        #
        #   class A1(Component):
        #       _name = 'a'                          Component
        #                                            /  / \  \
        #   class B1(Component):                    /  A2 A1  \
        #       _name = 'b'                        /   \  /    \
        #                                         B2 ComponentA B1
        #   class B2(Component):                   \     |     /
        #       _name = 'b'                         \    |    /
        #       _inherit = ['a', 'b']                \   |   /
        #                                            ComponentB
        #   class A2(Component):
        #       _inherit = 'a'

        # determine inherited components
        parents = cls._inherit
        if isinstance(parents, basestring):
            parents = [parents]
        elif parents is None:
            parents = []

        # determine the component's name
        name = cls._name or (len(parents) == 1 and parents[0]) or cls.__name__

        # all components except 'base' implicitly inherit from 'base'
        if name != 'base':
            parents = list(parents) + ['base']

        # create or retrieve the component's class
        if name in parents:
            if name not in registry:
                raise TypeError("Component %r does not exist in registry." %
                                name)
            ComponentClass = registry[name]
        else:
            ComponentClass = type(name, (Component,), {
                '_name': name,
                '_register': False,
                # names of children component
                '_inherit_children': OrderedSet(),
            })

        # determine all the classes the component should inherit from
        bases = LastOrderedSet([cls])
        for parent in parents:
            if parent not in registry:
                raise TypeError(
                    "Component %r inherits from non-existing component %r." %
                    (name, parent)
                )
            parent_class = registry[parent]
            if parent == name:
                for base in parent_class.__bases__:
                    bases.add(base)
            else:
                bases.add(parent_class)
                parent_class._inherit_children.add(name)
        ComponentClass.__bases__ = tuple(bases)

        # determine the attributes of the component's class
        ComponentClass._build_component_attributes(registry)

        registry[name] = ComponentClass

        return ComponentClass

    @classmethod
    def _build_component_attributes(cls, registry):
        """ Initialize base component attributes. """
        # TODO: see if we concatenate models, usage, ...
