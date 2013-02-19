# -*- coding: utf-8 -*-

import unittest2

from openerp.addons.connector.reference import (
        Reference,
        get_reference,
        REFERENCES)
from openerp.addons.connector import Binder
from openerp.addons.connector import (Mapper,
                                                       ImportMapper,
                                                       ExportMapper)
from openerp.addons.connector import BackendAdapter


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
        self.reference._classes.clear()

    def test_register_class(self):
        class BenderBinder(Binder):
            _model_name = 'res.users'

        self.reference.register_class(BenderBinder)
        ref = self.reference.get_class(Binder, 'res.users')
        self.assertEqual(ref, BenderBinder)

    def test_register_class_decorator(self):
        @self.reference
        class ZoidbergMapper(ExportMapper):
            _model_name = 'res.users'

        ref = self.reference.get_class(ExportMapper, 'res.users')
        self.assertEqual(ref, ZoidbergMapper)

    def test_register_class_parent(self):
        """ It should get the parent's class when no class is defined"""
        @self.parent
        class FryBinder(Binder):
            _model_name = 'res.users'

        ref = self.reference.get_class(Binder, 'res.users')
        self.assertEqual(ref, FryBinder)

    def test_no_register_error(self):
        """ Error when asking for a class and none is found"""
        with self.assertRaises(ValueError):
            ref = self.reference.get_class(BackendAdapter, 'res.users')

    def test_registered_classes_all(self):
        @self.reference
        class LeelaMapper(Mapper):
            _model_name = 'res.users'

        @self.reference
        class FarnsworthBinder(Binder):
            _model_name = 'res.users'

        @self.reference
        class NibblerBackendAdapter(BackendAdapter):
            _model_name = 'res.users'

        classes = list(self.reference.registered_classes())
        self.assertItemsEqual(
                classes,
                [LeelaMapper, FarnsworthBinder, NibblerBackendAdapter])

    def test_registered_classes_filter(self):
        @self.reference
        class LeelaMapper(ExportMapper):
            _model_name = 'res.users'

        @self.reference
        class AmyWongMapper(ImportMapper):
            _model_name = 'res.users'

        @self.reference
        class FarnsworthBinder(Binder):
            _model_name = 'res.users'

        @self.reference
        class NibblerBackendAdapter(BackendAdapter):
            _model_name = 'res.users'

        classes = list(self.reference.registered_classes(Mapper))
        self.assertItemsEqual(
                classes,
                [LeelaMapper, AmyWongMapper])
