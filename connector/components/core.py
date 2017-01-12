# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# Copyright 2017 Odoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from collections import defaultdict

from odoo.tools import OrderedSet, LastOrderedSet
from ..connector import _get_addon_name


class MetaComponent(type):

    components = defaultdict(list)

    def __init__(self, name, bases, attrs):
        if not self._register:
            self._register = True
            super(MetaComponent, self).__init__(name, bases, attrs)
            return

        if not hasattr(self, '_module'):
            self._module = _get_addon_name(self.__module__)

        self.components[self._module].append(self)


class Component(object):
    __metaclass__ = MetaComponent

    _register = False

    _name = None
    _inherit = None

    _apply_on = None  # None means any Model, can be a list ['res.users', ...]
    _usage = None  # component purpose, might be a list? ['import.mapper', ...]

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
        # TODO: see if we concatenate models, purpose, ...
