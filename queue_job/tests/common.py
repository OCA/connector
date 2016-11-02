# -*- coding: utf-8 -*-

from contextlib import contextmanager
from odoo.addons.queue_job.job import job, JOB_REGISTRY, related_action


def start_jobify(method, **kwargs):
    job(method, **kwargs)


def stop_jobify(method):
    JOB_REGISTRY.remove(method)
    attrs = ('delayable', 'delay', 'retry_pattern', 'default_channel')
    for attr in attrs:
        if hasattr(method.__func__, attr):
            delattr(method.__func__, attr)


@contextmanager
def jobify(method, **kwargs):
    try:
        start_jobify(method, **kwargs)
        yield
    finally:
        stop_jobify(method)


def start_related_actionify(method, **kwargs):
    related_action(**kwargs)(method)


def stop_related_actionify(method):
    attrs = ('related_action',)
    for attr in attrs:
        if hasattr(method.__func__, attr):
            delattr(method.__func__, attr)


@contextmanager
def related_actionify(method, **kwargs):
    try:
        start_related_actionify(method, **kwargs)
        yield
    finally:
        stop_related_actionify(method)
