# -*- coding: utf-8 -*-

import unittest2

from openerp.addons.connector.backend import (
        Backend,
        get_backend,
        BACKENDS)
from openerp.addons.connector import Binder
from openerp.addons.connector import (Mapper,
                                                       ImportMapper,
                                                       ExportMapper)
from openerp.addons.connector import BackendAdapter


class test_backend(unittest2.TestCase):
    """ Test Backend """

    def setUp(self):
        self.service = 'calamitorium'

    def tearDown(self):
        BACKENDS.backends.clear()

    def test_new_backend(self):
        """ Create a backend"""
        version = '1.14'
        backend = Backend(self.service, version=version)
        self.assertEqual(backend.service, self.service)
        self.assertEqual(backend.version, version)

    def test_parent(self):
        """ Bind the backend to a parent backend"""
        version = '1.14'
        backend = Backend(self.service)
        child_backend = Backend(parent=backend, version=version)
        self.assertEqual(child_backend.service, backend.service)

    def test_no_service(self):
        """ Should raise an error because no service or parent is defined"""
        with self.assertRaises(ValueError):
            backend = Backend(version='1.14')

    def test_get_backend(self):
        """ Find a backend """
        backend = Backend(self.service)
        found_ref = get_backend(self.service)
        self.assertEqual(backend, found_ref)

    def test_backend_version(self):
        """ Find a backend with a version """
        parent = Backend(self.service)
        backend = Backend(parent=parent, version='1.14')
        found_ref = get_backend(self.service, version='1.14')
        self.assertEqual(backend, found_ref)


class test_backend_register(unittest2.TestCase):
    """ Test registration of classes on the Backend"""


    def setUp(self):
        self.service = 'calamitorium'
        self.version = '1.14'
        self.parent = Backend(self.service)
        self.backend = Backend(parent=self.parent, version=self.version)

    def tearDown(self):
        BACKENDS.backends.clear()
        self.backend._classes.clear()

    def test_register_class(self):
        class BenderBinder(Binder):
            _model_name = 'res.users'

        self.backend.register_class(BenderBinder)
        ref = self.backend.get_class(Binder, 'res.users')
        self.assertEqual(ref, BenderBinder)

    def test_register_class_decorator(self):
        @self.backend
        class ZoidbergMapper(ExportMapper):
            _model_name = 'res.users'

        ref = self.backend.get_class(ExportMapper, 'res.users')
        self.assertEqual(ref, ZoidbergMapper)

    def test_register_class_parent(self):
        """ It should get the parent's class when no class is defined"""
        @self.parent
        class FryBinder(Binder):
            _model_name = 'res.users'

        ref = self.backend.get_class(Binder, 'res.users')
        self.assertEqual(ref, FryBinder)

    def test_no_register_error(self):
        """ Error when asking for a class and none is found"""
        with self.assertRaises(ValueError):
            ref = self.backend.get_class(BackendAdapter, 'res.users')

    def test_registered_classes_all(self):
        @self.backend
        class LeelaMapper(Mapper):
            _model_name = 'res.users'

        @self.backend
        class FarnsworthBinder(Binder):
            _model_name = 'res.users'

        @self.backend
        class NibblerBackendAdapter(BackendAdapter):
            _model_name = 'res.users'

        classes = list(self.backend.registered_classes())
        self.assertItemsEqual(
                classes,
                [LeelaMapper, FarnsworthBinder, NibblerBackendAdapter])

    def test_registered_classes_filter(self):
        @self.backend
        class LeelaMapper(ExportMapper):
            _model_name = 'res.users'

        @self.backend
        class AmyWongMapper(ImportMapper):
            _model_name = 'res.users'

        @self.backend
        class FarnsworthBinder(Binder):
            _model_name = 'res.users'

        @self.backend
        class NibblerBackendAdapter(BackendAdapter):
            _model_name = 'res.users'

        classes = list(self.backend.registered_classes(Mapper))
        self.assertItemsEqual(
                classes,
                [LeelaMapper, AmyWongMapper])
