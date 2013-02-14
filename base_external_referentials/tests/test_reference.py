# -*- coding: utf-8 -*-

import unittest2

from openerp.addons.base_external_referentials.reference import (
        Reference,
        get_reference,
        REFERENCES)
from openerp.addons.base_external_referentials.synchronizer import (
        Synchronizer)
from openerp.addons.base_external_referentials.binder import (
        Binder)
from openerp.addons.base_external_referentials.mapper import (
        Mapper)
from openerp.addons.base_external_referentials.backend_adapter import (
        BackendAdapter)


class test_reference(unittest2.TestCase):
    """ Test Reference """

    def setUp(self):
        self.service = 'calamitorium'

    def tearDown(self):
        REFERENCES.references.clear()

    def test_new_reference(self):
        """ Create a reference"""
        version = '1.14'
        reference = Reference(self.service, version=version)
        self.assertEqual(reference.service, self.service)
        self.assertEqual(reference.version, version)

    def test_parent(self):
        """ Bind the reference to a parent reference"""
        version = '1.14'
        reference = Reference(self.service)
        child_reference = Reference(parent=reference, version=version)
        self.assertEqual(child_reference.service, reference.service)

    def test_no_service(self):
        """ Should raise an error because no service or parent is defined"""
        with self.assertRaises(ValueError):
            reference = Reference(version='1.14')

    def test_get_reference(self):
        """ Find a reference """
        reference = Reference(self.service)
        found_ref = get_reference(self.service)
        self.assertEqual(reference, found_ref)

    def test_reference_version(self):
        """ Find a reference with a version """
        parent = Reference(self.service)
        reference = Reference(parent=parent, version='1.14')
        found_ref = get_reference(self.service, version='1.14')
        self.assertEqual(reference, found_ref)


class test_reference_register(unittest2.TestCase):
    """ Test registration of classes on the Reference"""


    def setUp(self):
        self.service = 'calamitorium'
        self.version = '1.14'
        self.parent = Reference(self.service)
        self.reference = Reference(parent=self.parent, version=self.version)

    def tearDown(self):
        REFERENCES.references.clear()

    def test_register_synchronizer(self):
        class FrySynchronizer(Synchronizer):
            pass

        self.reference.register_synchronizer(FrySynchronizer)
        ref = self.reference.get_synchronizer('export', 'res.users')
        self.assertEqual(ref, FrySynchronizer)
        self.reference.unregister_synchronizer(FrySynchronizer)
        with self.assertRaises(ValueError):
            self.reference.get_synchronizer('export', 'res.users')

    def test_register_mapper(self):
        class ZoidbergMapper(Mapper):
            pass

        self.reference.register_mapper(ZoidbergMapper)
        ref = self.reference.get_mapper('res.users', 'out')
        self.assertEqual(ref, ZoidbergMapper)
        self.reference.unregister_mapper(ZoidbergMapper)
        with self.assertRaises(ValueError):
            self.reference.get_mapper('export', 'res.users')

    def test_register_binder(self):
        class BenderBinder(Binder):
            pass

        self.reference.register_binder(BenderBinder)
        ref = self.reference.get_binder('res.users')
        self.assertEqual(ref, BenderBinder)
        self.reference.unregister_binder(BenderBinder)
        with self.assertRaises(ValueError):
            self.reference.get_binder('export', 'res.users')

    def test_register_backend_adapter(self):
        class HermesBackendAdapter(BackendAdapter):
            pass

        self.reference.register_backend_adapter(HermesBackendAdapter)
        ref = self.reference.get_backend_adapter('res.users')
        self.assertEqual(ref, HermesBackendAdapter)
        self.reference.unregister_backend_adapter(HermesBackendAdapter)
        with self.assertRaises(ValueError):
            self.reference.get_backend_adapter('export', 'res.users')

    def test_register_synchronizer_decorator(self):
        @self.reference
        class FrySynchronizer(Synchronizer):
            pass

        ref = self.reference.get_synchronizer('export', 'res.users')
        self.assertEqual(ref, FrySynchronizer)

    def test_register_mapper_decorator(self):
        @self.reference
        class ZoidbergMapper(Mapper):
            pass

        ref = self.reference.get_mapper('res.users', 'out')
        self.assertEqual(ref, ZoidbergMapper)

    def test_register_binder_decorator(self):
        @self.reference
        class BenderBinder(Binder):
            pass

        ref = self.reference.get_binder('res.users')
        self.assertEqual(ref, BenderBinder)

    def test_register_backend_adapter_decorator(self):
        @self.reference
        class HermesBackendAdapter(BackendAdapter):
            pass

        ref = self.reference.get_backend_adapter('res.users')
        self.assertEqual(ref, HermesBackendAdapter)

    def test_register_binder_parent(self):
        """ It should get the parent's binder when no binder is defined"""
        @self.parent
        class LeelaBinder(Binder):
            pass

        ref = self.reference.get_binder('res.users')
        self.assertEqual(ref, LeelaBinder)

    def test_register_synchronizer_parent(self):
        """ It should get the parent's synchronizer when no synchronizer
        is defined"""
        @self.parent
        class AmySynchronizer(Synchronizer):
            pass

        ref = self.reference.get_synchronizer('export', 'res.users')
        self.assertEqual(ref, AmySynchronizer)

    def test_register_mapper_parent(self):
        """ It should get the parent's mapper when no mapper is defined"""
        @self.parent
        class FarnsworthMapper(Mapper):
            pass

        ref = self.reference.get_mapper('res.users', 'out')
        self.assertEqual(ref, FarnsworthMapper)

    def test_register_backend_adapter_parent(self):
        """ It should get the parent's backend_adapter when no
        backend_adapter is defined"""
        @self.parent
        class BranniganBackendAdapter(BackendAdapter):
            pass

        ref = self.reference.get_backend_adapter('res.users')
        self.assertEqual(ref, BranniganBackendAdapter)

    def test_no_register_error_synchronizer(self):
        """ Error when asking for a synchronizer when any is found"""
        with self.assertRaises(ValueError):
            ref = self.reference.get_synchronizer('export', 'res.users')

    def test_no_register_error_mapper(self):
        """ Error when asking for a mapper when any is found"""
        with self.assertRaises(ValueError):
            ref = self.reference.get_mapper('res.users', 'out')

    def test_no_register_error_binder(self):
        """ Error when asking for a binder when any is found"""
        with self.assertRaises(ValueError):
            ref = self.reference.get_binder('res.users')

    def test_no_register_error_backend_adapter(self):
        """ Error when asking for a backend_adapter when any is found"""
        with self.assertRaises(ValueError):
            ref = self.reference.get_backend_adapter('res.users')
