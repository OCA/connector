# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of connector, an Odoo module.
#
#     Author: Stéphane Bidoul <stephane.bidoul@acsone.eu>
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     connector is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     connector is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with connector.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime
from heapq import heappush, heappop
import logging
from weakref import WeakValueDictionary

_logger = logging.getLogger(__name__)


STATE_PENDING = 'pending'
STATE_ENQUEUED = 'enqueued'
STATE_STARTED = 'started'
STATE_FAILED = 'failed'
STATE_DONE = 'done'

STATES_NOT_DONE = (STATE_PENDING, STATE_ENQUEUED, STATE_STARTED, STATE_FAILED)


class PriorityQueue:
    """A priority queue that supports removing arbitrary objects.

    Adding an object already in the queue is a no op.
    Popping an empty queue returns None.

    >>> q = PriorityQueue()
    >>> q.add(2)
    >>> q.add(3)
    >>> q.add(3)
    >>> q.add(1)
    >>> q[0]
    1
    >>> len(q)
    3
    >>> q.pop()
    1
    >>> q.remove(2)
    >>> len(q)
    1
    >>> q[0]
    3
    >>> q.pop()
    3
    >>> q.pop()
    >>> q.add(2)
    >>> q.remove(2)
    >>> q.add(2)
    >>> q.pop()
    2
    """

    def __init__(self):
        self._heap = []
        self._known = set()    # all objects in the heap (including removed)
        self._removed = set()  # all objects that have been removed

    def __len__(self):
        return len(self._known) - len(self._removed)

    def __getitem__(self, i):
        if i != 0:
            raise IndexError()
        while True:
            if not self._heap:
                raise IndexError()
            o = self._heap[0]
            if o in self._removed:
                o2 = heappop(self._heap)
                assert o2 == o
                self._removed.remove(o)
                self._known.remove(o)
            else:
                return o

    def __contains__(self, o):
        return o in self._known and o not in self._removed

    def add(self, o):
        if o is None:
            raise ValueError()
        if o in self._removed:
            self._removed.remove(o)
        if o in self._known:
            return
        self._known.add(o)
        heappush(self._heap, o)

    def remove(self, o):
        if o is None:
            raise ValueError()
        if o not in self._known:
            return
        if o not in self._removed:
            self._removed.add(o)

    def pop(self):
        while True:
            try:
                o = heappop(self._heap)
            except IndexError:
                # queue is empty
                return None
            self._known.remove(o)
            if o in self._removed:
                self._removed.remove(o)
            else:
                return o


class SafeSet(set):
    """A set that does not raise KeyError when removing non-existent items.

    >>> s = SafeSet()
    >>> s.remove(1)
    >>> len(s)
    0
    >>> s.remove(1)
    """
    def remove(self, o):
        try:
            super(SafeSet, self).remove(o)
        except KeyError:
            pass


class ChannelJob:
    """A channel job is attached to a channel and holds the properties of a
    job that are necessary to prioritise them.

    Channel jobs are comparable according to the following rules:
        * jobs with an eta come before all other jobs
        * then jobs with a smaller eta come first
        * then jobs with smaller priority come first
        * then jobs with a smaller creation time come first
        * then jobs with a samller sequence come first

    Here are some examples.

    j1 comes before j2 before it has a smaller date_created
    >>> j1 = ChannelJob(None, 1, seq=0, date_created=1, priority=9, eta=None)
    >>> j1
    <ChannelJob 1>
    >>> j2 = ChannelJob(None, 2, seq=0, date_created=2, priority=9, eta=None)
    >>> j1 < j2
    True

    j3 comes first because it has lower priority,
    despite having a creation date after j1 and j2
    >>> j3 = ChannelJob(None, 3, seq=0, date_created=3, priority=2, eta=None)
    >>> j3 < j1
    True

    j4 and j5 comes even before j3, because they have an eta
    >>> j4 = ChannelJob(None, 4, seq=0, date_created=4, priority=9, eta=9)
    >>> j5 = ChannelJob(None, 5, seq=0, date_created=5, priority=9, eta=9)
    >>> j4 < j5 < j3
    True

    j6 has same date_created and priority as j5 but a smaller eta
    >>> j6 = ChannelJob(None, 6, seq=0, date_created=5, priority=9, eta=2)
    >>> j6 < j4 < j5
    True

    Here is the complete suite:
    >>> j6 < j4 < j5 < j3 < j1 < j2
    True

    j0 has the same properties as j1 but they are not considered
    equal as they are different instances
    >>> j0 = ChannelJob(None, 1, seq=0, date_created=1, priority=9, eta=None)
    >>> j0 == j1
    False
    >>> j0 == j0
    True
    """

    def __init__(self, db_name, channel, uuid,
                 seq, date_created, priority, eta):
        self.db_name = db_name
        self.channel = channel
        self.uuid = uuid
        self.seq = seq
        self.date_created = date_created
        self.priority = priority
        self.eta = eta

    def __repr__(self):
        return "<ChannelJob %s>" % self.uuid

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)

    def __cmp__(self, other):
        if self.eta and not other.eta:
            return -1
        elif not self.eta and other.eta:
            return 1
        else:
            return (cmp(self.eta, other.eta) or
                    cmp(self.priority, other.priority) or
                    cmp(self.date_created, other.date_created))


class ChannelQueue:
    """A channel queue is a priority queue for jobs, that returns
    jobs with a past ETA first.

    >>> q = ChannelQueue()
    >>> j1 = ChannelJob(None, 1, seq=0, date_created=1, priority=1, eta=10)
    >>> j2 = ChannelJob(None, 2, seq=0, date_created=2, priority=1, eta=None)
    >>> j3 = ChannelJob(None, 3, seq=0, date_created=3, priority=1, eta=None)
    >>> q.add(j1)
    >>> q.add(j2)
    >>> q.add(j3)
    >>> q.pop(now=1)
    <ChannelJob 2>
    >>> q.pop(now=11)
    <ChannelJob 1>
    >>> q.pop(now=12)
    <ChannelJob 3>
    """

    def __init__(self):
        self._queue = PriorityQueue()
        self._eta_queue = PriorityQueue()

    def __len__(self):
        return len(self._eta_queue) + len(self._queue)

    def __contains__(self, o):
        return o in self._eta_queue or o in self._queue

    def add(self, job):
        if job.eta:
            self._eta_queue.add(job)
        else:
            self._queue.add(job)

    def remove(self, job):
        self._eta_queue.remove(job)
        self._queue.remove(job)

    def pop(self, now):
        if len(self._eta_queue) and self._eta_queue[0].eta <= now:
            return self._eta_queue.pop()
        else:
            return self._queue.pop()


class Channel:
    """A channel for jobs, with a maximum number of workers.

    Job channels are joined in a hierarchy down to the root channel.
    When a job channel has free workers, jobs are dequeued, marked
    as running in the channel and are inserted into the queue of the
    parent channel where they wait for free workers and so on.

    Job channels can be visualized as water channels with a given flow
    limit (= workers). Channels are joined together in a downstream channel
    and the flow limit of the downstream channel limit upstream channels.

    ---------------------+
                         |
                         |
     Ch. A W:4,Q:12,R:4  +-----------------------

    ---------------------+  Ch. root W:5,Q:0,R:4
                         |
    ---------------------+
     Ch. B W:1,Q:0,R:0
    ---------------------+-----------------------

    The above diagram illustrates two channels joining in the root channel.
    The root channel has 5 workers, and 4 running jobs coming from Channel A.
    Channel A has maximum 4 workers, all in use (passed down to the root
    channel), and 12 jobs enqueued. Channel B has maximum 1 worker,
    none in use. This means that whenever a new job comes in channel B,
    there will be available room for it to run in the root channel.

    Note that from the point of view of a channel, 'running' means enqueued
    in the downstream channel. Only jobs marked running in the root channel
    are actually sent to Odoo for execution.

    Should a downstream channel have less capacity than its upstream channels,
    jobs going downstream will be enqueued in the downstream channel,
    and compete normally according to their properties (priority, etc).

    Using this technique, it is possible to enforce sequence in a channel
    with 1 worker. It is also possible to dedicate a channel with a
    limited number of workers for application-autocreated subchannels
    without risking to overflow the system.
    """

    def __init__(self, name, parent, workers=1, sequential=False):
        self.name = name
        self.parent = parent
        if self.parent:
            self.parent.children.append(self)
        self.children = []
        self.workers = None
        self.sequential = False
        self._queue = ChannelQueue()
        self._running = SafeSet()
        self._failed = SafeSet()

    def configure(self, config):
        assert config['name'] == self.fullname
        self.workers = config.get('workers', 1)
        self.sequential = bool(config.get('sequential', False))
        if self.sequential and self.workers != 1:
            raise ValueError("A sequential channel can have only one worker")

    @property
    def fullname(self):
        if self.parent:
            return self.parent.fullname + '.' + self.name
        else:
            return self.name

    def get_subchannel_by_name(self, subchannel_name):
        for child in self.children:
            if child.name == subchannel_name:
                return child
        return None

    def __str__(self):
        return "%s(W:%d,Q:%d,R:%d,F:%d)" % (self.name,
                                            self.workers,
                                            len(self._queue),
                                            len(self._running),
                                            len(self._failed))

    def remove(self, job):
        self._queue.remove(job)
        self._running.remove(job)
        self._failed.remove(job)
        if self.parent:
            self.parent.remove(job)

    def set_done(self, job):
        self.remove(job)
        _logger.debug("job %s marked done in channel %s",
                      job.uuid, self.name)

    def set_pending(self, job):
        if job not in self._queue:
            self._queue.add(job)
            self._running.remove(job)
            self._failed.remove(job)
            if self.parent:
                self.parent.remove(job)
            _logger.debug("job %s marked pending in channel %s",
                          job.uuid, self.name)

    def set_running(self, job):
        if job not in self._running:
            self._queue.remove(job)
            self._running.add(job)
            self._failed.remove(job)
            if self.parent:
                self.parent.set_running(job)
            _logger.debug("job %s marked running in channel %s",
                          job.uuid, self.name)

    def set_failed(self, job):
        if job not in self._failed:
            self._queue.remove(job)
            self._running.remove(job)
            self._failed.add(job)
            if self.parent:
                self.parent.remove(job)
            _logger.debug("job %s marked failed in channel %s",
                          job.uuid, self.name)

    def get_jobs_to_run(self):
        # enqueue jobs of children channels
        for child in self.children:
            for job in child.get_jobs_to_run():
                self._queue.add(job)
        # sequential channels block when there are failed jobs
        # TODO: this is probably not sufficient to ensure
        #       senquentiality because of the behaviour in presence
        #       of jobs with eta; plus: check if there are no
        #       race conditions.
        if self.sequential and len(self._failed):
            return
        # yield jobs that are ready to run
        while not self.workers or len(self._running) < self.workers:
            job = self._queue.pop(now=datetime.now())
            if not job:
                return
            self._running.add(job)
            _logger.debug("job %s marked running in channel %s",
                          job.uuid, self.name)
            _logger.debug("channel %s", self)
            yield job


class ChannelManager:

    def __init__(self):
        self._jobs_by_uuid = WeakValueDictionary()
        self._root_channel = Channel(name='root', parent=None)
        self._channels_by_name = WeakValueDictionary(root=self._root_channel)

    @classmethod
    def parse_simple_config(cls, config_string):
        """Parse a simple channels configuration string.

        The general form is as follow:
        channel.subchannel.subsubchannel(:workers(:key=value)*)?,...

        Returns a list of channel configuration dictionaries.

        >>> from pprint import pprint as pp
        >>> pp(ChannelManager.parse_simple_config('root:4'))
        [{'name': 'root', 'workers': 4}]
        >>> pp(ChannelManager.parse_simple_config('root:4,root.sub:2'))
        [{'name': 'root', 'workers': 4}, {'name': 'root.sub', 'workers': 2}]
        >>> pp(ChannelManager.parse_simple_config('root:4,root.sub:2:'
        ...                                       'sequential:k=v'))
        [{'name': 'root', 'workers': 4},
         {'k': 'v', 'name': 'root.sub', 'sequential': True, 'workers': 2}]
        >>> pp(ChannelManager.parse_simple_config('root'))
        [{'name': 'root', 'workers': 1}]
        """
        res = []
        for channel_config_string in config_string.split(','):
            config = {}
            config_items = channel_config_string.split(':')
            name = config_items[0]
            if not name:
                raise ValueError('Invalid channel config %s: '
                                 'missing channel name' % config_string)
            config['name'] = name
            if len(config_items) > 1:
                workers = config_items[1]
                try:
                    config['workers'] = int(workers)
                except:
                    raise ValueError('Invalid channel config %s: '
                                     'invalid workers %s' %
                                     (config_string, workers))
                for config_item in config_items[2:]:
                    kv = config_item.split('=')
                    if len(kv) == 1:
                        k, v = kv[0], True
                    elif len(kv) == 2:
                        k, v = kv
                    else:
                        raise ValueError('Invalid channel config %s: ',
                                         'incorrect config item %s'
                                         (config_string, config_item))
                    if k in config:
                        raise ValueError('Invalid channel config %s: '
                                         'duplicate key %s'
                                         (config_string, k))
                    config[k] = v
            else:
                config['workers'] = 1
            res.append(config)
        return res

    def simple_configure(self, config_string):
        for config in ChannelManager.parse_simple_config(config_string):
            self.get_channel_from_config(config)

    def get_channel_from_config(self, config):
        channel = self.get_channel_by_name(config['name'], autocreate=True)
        channel.configure(config)
        return channel

    def get_channel_by_name(self, channel_name, autocreate):
        """
        >>> cm = ChannelManager()
        >>> c = cm.get_channel_by_name('root', autocreate=False)
        >>> c.name
        'root'
        >>> c.fullname
        'root'
        >>> c = cm.get_channel_by_name('root.sub', autocreate=True)
        >>> c.name
        'sub'
        >>> c.fullname
        'root.sub'
        >>> c = cm.get_channel_by_name('sub', autocreate=True)
        >>> c.name
        'sub'
        >>> c.fullname
        'root.sub'
        """
        if channel_name in self._channels_by_name:
            return self._channels_by_name[channel_name]
        if not autocreate:
            raise RuntimeError('Channel %s not found' % channel_name)
        parent = self._root_channel
        for subchannel_name in channel_name.split('.'):
            if subchannel_name == 'root':
                continue
            subchannel = parent.get_subchannel_by_name(subchannel_name)
            if not subchannel:
                subchannel = Channel(subchannel_name, parent)
                self._channels_by_name[subchannel.fullname] = subchannel
            parent = subchannel
        return parent

    def notify(self, db_name, channel_config_string, uuid,
               seq, date_created, priority, eta, state):
        if not channel_config_string:
            channel = self._root_channel
        else:
            configs = ChannelManager.parse_simple_config(channel_config_string)
            if len(configs) != 1:
                raise ValueError('%s is not a configuration for '
                                 'a single channel' % channel_config_string)
            channel = self.get_channel_from_config(configs[0])
        job = self._jobs_by_uuid.get(uuid)
        if not job:
            job = ChannelJob(db_name, channel, uuid,
                             seq, date_created, priority, eta)
            self._jobs_by_uuid[uuid] = job
        # TODO: handle sequence change
        assert job.seq == seq
        # db_name is invariant
        assert job.db_name == db_name
        # date_created is invariant
        assert job.date_created == date_created
        # TODO: handle priority change
        assert job.priority == priority
        # TODO: handle eta change
        assert job.eta == eta
        # TODO: handle channel change
        assert job.channel == channel
        # state transitions
        if not state or state == STATE_DONE:
            channel.set_done(job)
        elif state == STATE_PENDING:
            channel.set_pending(job)
        elif state in (STATE_ENQUEUED, STATE_STARTED):
            channel.set_running(job)
        elif state == STATE_FAILED:
            channel.set_failed(job)
        else:
            _logger.error("unexpected state %s for job %s", state, job)
        # _logger.debug("channel %s", self._root_channel)

    def remove_job(self, uuid):
        job = self._jobs_by_uuid.get(uuid)
        if job:
            job.channel.remove(job)

    def remove_db(self, db_name):
        for job in self._jobs_by_uuid.values():
            if job.db_name == db_name:
                job.channel.remove(job)

    def get_jobs_to_run(self):
        return self._root_channel.get_jobs_to_run()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
