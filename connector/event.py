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
    """ An event contains consumers called when the event is fired.

    The events are able to filter the consumers to execute by model name.

    The usage of an event is to instantiate an `Event` object::

        on_my_event = Event()

    Then to subscribe one or more consumers, a consumer is a function::

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
            print "Consumer 2"
            print ("Event was fired on a product "
                  "with arguments: %s, %s" % (a, b))

        on_my_event.subscribe(do_something_product2,
                              replacing=do_something_product)

    Finally, we fire the event::

        on_my_event.fire('value_a', 'value_b')

    A consumer can be subscribed using a decorator::

        @on_my_event
        def do_other_thing(a, b):
            print 'foo'

        @on_my_event(replacing=do_other_thing)
        def print_bar(a, b):
            print 'bar'

    """

    def __init__(self):
        self._consumers = {None: set()}

    def subscribe(self, consumer, model_names=None, replacing=None):
        """ Subscribe a consumer on the event

        :param consumer: the function to register on the event
        :param model_names: the consumer will be active only on these models,
            active on all models if ``None``
        :param replacing: the function beeing replaced by this new one.
        """
        if replacing is not None:
            self.unsubscribe(replacing, model_names=model_names)
        if not hasattr(model_names, '__iter__'):
            model_names = [model_names]
        for name in model_names:
            self._consumers.setdefault(name, set()).add(consumer)

    def unsubscribe(self, consumer, model_names=None):
        """ Remove a consumer from the event

        :param consumer: the function to unsubscribe
        :param model_names: remove only for these models or remove a
            consumer which is active on all models if ``None``.
        """
        if not hasattr(model_names, '__iter__'):
            model_names = [model_names]
        for name in model_names:
            if name in self._consumers:
                self._consumers[name].discard(consumer)

    def has_consumer_for(self, model_name):
        """ Return True if at least one consumer is registered
        for the model.
        """
        if self._consumers[None]:
            return True  # at least 1 global consumer exist
        return bool(self._consumers.get(model_name))

    def fire(self, model_name, *args, **kwargs):
        """ Call each consumer subscribed on the event with the given
        arguments and keyword arguments.

        All the consumers which were subscribed globally (no model name) or
        which are subscribed on the same model

        :param model_name: the current model
        :param args: arguments propagated to the consumer
        :param kwargs: keyword arguments propagated to the consumer
        """
        for name in (None, model_name):
            for consumer in self._consumers.get(name, ()):
                consumer(*args, **kwargs)

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
