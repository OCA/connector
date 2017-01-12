# -*- coding: utf-8 -*-
# Copyright 2015-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import importlib
from contextlib import contextmanager

import mock


@contextmanager
def mock_job_delay_to_direct(job_path):
    """ Replace the .delay() of a job by a direct call

    job_path is the python path as string, such as::

      'odoo.addons.magentoerpconnect.stock_picking.export_picking_done'

    This is a context manager, all the calls made to the job function in
    job_path inside the context manager will be executed synchronously.

    .. note:: It uses :meth:`mock.patch` so it has the same pitfall
              regarding the python path.  If the mock seems to have no
              effect, read `Where to patch
              <http://www.voidspace.org.uk/python/mock/patch.html#where-to-patch>`_
              in the mock documentation.

    """
    job_module, job_name = job_path.rsplit('.', 1)
    module = importlib.import_module(job_module)
    job_func = getattr(module, job_name, None)
    assert job_func, "The function %s must exist in %s" % (job_name,
                                                           job_module)

    def clean_args_for_func(*args, **kwargs):
        # remove the special args reserved to '.delay()'
        kwargs.pop('priority', None)
        kwargs.pop('eta', None)
        kwargs.pop('model_name', None)
        kwargs.pop('max_retries', None)
        kwargs.pop('description', None)
        job_func(*args, **kwargs)

    with mock.patch(job_path) as patched_job:
        # call the function directly instead of '.delay()'
        patched_job.delay.side_effect = clean_args_for_func
        yield patched_job
