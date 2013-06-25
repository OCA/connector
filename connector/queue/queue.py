# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
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
from __future__ import absolute_import
from Queue import PriorityQueue


class JobsQueue(object):
    """ Holds the jobs planned for execution in memory.

    The Jobs are sorted, the higher the priority is,
    the earlier the jobs are dequeued.
    """

    def __init__(self):
        self._queue = PriorityQueue()

    def enqueue(self, job):
        self._queue.put_nowait(job)

    def dequeue(self):
        """ Take the first job according to its priority
        and return it"""
        return self._queue.get()
