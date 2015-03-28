import logging
from threading import Thread
import time

from openerp.service import db
from openerp.service import server

from . import channels
from .runner import OdooConnectorRunner

_logger = logging.getLogger(__name__)

START_DELAY = 10


def run():
    # sleep a bit to let the workers start at ease
    time.sleep(START_DELAY)
    _logger.info("dbs: %s", db.exp_list())
    OdooConnectorRunner().run_forever()


# monkey patch the Odoo server to start the job runner thread
# once in the main process and in the main process only
# (ie not in forked workers)

orig_prefork_start = server.PreforkServer.start
orig_threaded_start = server.ThreadedServer.start
orig_gevent_start = server.GeventServer.start


def prefork_start(server, *args, **kwargs):
    res = orig_prefork_start(server, *args, **kwargs)
    _logger.error("jobrunner prefork start")
    thread = Thread(target=run)
    thread.daemon = True
    thread.start()
    return res


def threaded_start(server, *args, **kwargs):
    res = orig_threaded_start(server, *args, **kwargs)
    _logger.error("jobrunner threaded start")
    thread = Thread(target=run)
    thread.daemon = True
    thread.start()
    return res


def gevent_start(server, *args, **kwargs):
    res = orig_gevent_start(server, *args, **kwargs)
    _logger.error("jobrunner gevent start")
    # TODO: gevent spawn?
    raise RuntimeError("not implemented")
    return res


server.PreforkServer.start = prefork_start
server.ThreadedServer.start = threaded_start
server.GeventServer.start = gevent_start
