# -*- coding: utf-8 -*-
# Part of Odoo 10. See Odoo LICENSE file for full copyright and licensing
# details.
# see odoo.tools.misc.py

from collections import MutableSet, OrderedDict


class OrderedSet(MutableSet):
    """ A set collection that remembers the elements first insertion order. """

    __slots__ = ["_map"]

    def __init__(self, elems=()):
        self._map = OrderedDict((elem, None) for elem in elems)

    def __contains__(self, elem):
        return elem in self._map

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def add(self, elem):
        self._map[elem] = None

    def discard(self, elem):
        self._map.pop(elem, None)


class LastOrderedSet(OrderedSet):
    """ A set collection that remembers the elements last insertion order. """

    def add(self, elem):
        OrderedSet.discard(self, elem)
        OrderedSet.add(self, elem)
