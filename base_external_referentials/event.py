# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012-2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from collections import Callable

__all__ = [
    'on_record_write',
    'on_record_create',
    'on_record_unlink',
    'on_workflow_signal',
]


class Event(object):
    """ An event contains actions called when the event is fired.

    The events are able to filter the actions to execute by model name.

    The usage of an event is to instantiate an `Event` object::

        on_my_event = Event()

    Then to subscribe one or more actions, an action is a function::

        def do_something(a, b):
            print "Event was fired with arguments: %s, %s" % (a, b)

        # active on all models
        on_my_event.subscribe(do_something)

        def do_something_product(a, b):
            print ("Event was fired on a product "
                  "with arguments: %s, %s" % (a, b))

        # active only on product.product
        on_my_event.subscribe(do_something_product,
                              model_names='product.product')

    We can also replace an event::

        def do_something_product2(a, b):
            print "Action 2"
            print ("Event was fired on a product "
                  "with arguments: %s, %s" % (a, b))

        on_my_event.subscribe(do_something_product2,
                              replacing=do_something_product)

    Finally, we fire the event::

        on_my_event.fire('value_a', 'value_b')

    An action can be subscribed using a decorator::

        @on_my_event
        def do_other_thing(a, b):
            print 'foo'

        @on_my_event(replacing=do_other_thing)
        def print_bar(a, b):
            print 'bar'

    """

    def __init__(self):
        self._actions = {None: set()}

    def subscribe(self, action, model_names=None, replacing=None):
        """ Subscribe an action on the event

        :param action: the function to register on the event
        :param model_names: the action will be active only on these models,
            active on all models if ``None``
        :param replacing: the function beeing replaced by this new one.
        """
        if replacing is not None:
            self.unsubscribe(replacing, model_names=model_names)
        if not hasattr(model_names, '__iter__'):
            model_names = [model_names]
        for name in model_names:
            self._actions.setdefault(name, set()).add(action)

    def unsubscribe(self, action, model_names=None):
        """ Remove an action from the event

        :param action: the function to unsubscribe
        :param model_names: remove only for these models or remove an
            action which is active on all models if ``None``.
        """
        if not hasattr(model_names, '__iter__'):
            model_names = [model_names]
        for name in model_names:
            if name in self._actions:
                self._actions[name].discard(action)

    def fire(self, model_name, *args, **kwargs):
        """ Call each action subscribed on the event with the given
        arguments and keyword arguments.

        All the action which were subscribed globally (no model name) or
        which are subscribed on the same model

        :param model_name: the current model
        :param args: arguments propagated to the action
        :param kwargs: keyword arguments propagated to the action
        """
        for name in (None, model_name):
            for action in self._actions.get(name, ()):
                action(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """ Event decorator

        For an event ``on_event`` declared like this::

            on_event = Event()

        A consumer can be subscribed using::

            @on_event
            def do_things(arg1, arg2):
                # work

        And for consumers specific to models::

            @on_event(model_names=['product.product', 'res.partner'])
            def do_things(arg1, arg2):
                # work

        The accepted arguments are those of :meth:`subscribe`.
        """
        def with_subscribe(**opts):
            def wrapped_func(func):
                self.subscribe(func, **opts)
                return func
            return wrapped_func

        if len(args) == 1 and isinstance(args[0], Callable):
            return with_subscribe(**kwargs)(*args)
        return with_subscribe(**kwargs)


on_record_write = Event()
"""
``on_record_write`` is fired when one record has been updated.

Listeners should take the following arguments:

 * session: `Session` object
 * record_id: id of the record
 * fields: name of the fields which have been written

"""

on_record_create = Event()
"""
``on_record_create`` is fired when one record has been created.

Listeners should take the following arguments:

 * session: `Session` object
 * record_id: id of the created record

"""

on_record_unlink = Event()
"""
``on_record_unlink`` is fired when one record has been deleted.

Listeners should take the following arguments:

 * session: `Session` object
 * record_id: id of the record

"""

on_workflow_signal = Event()
"""
``on_workflow_signal`` is fired when a workflow signal is triggered.

Listeners should take the following arguments:

 * session: `Session` object
 * record_id: id of the record
 * signal: name of the signal

"""
