# -*- coding: utf-8 -*-

import unittest2
import mock

from openerp.addons.connector.unit.mapper import (
        Mapper, changed_by, mapping)


class test_mapper(unittest2.TestCase):
    """ Test Mapper """

    def test_mapping_decorator(self):
        class KifKrokerMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @mapping
            def name(self):
                pass

            @changed_by('email')
            @mapping
            def email(self):
                pass

        self.assertEqual(
                KifKrokerMapper._map_methods,
                {'name': set(('name', 'city')),
                 'email': set(('email',))})

    def test_mapping_decorator_cross_classes(self):
        """ Mappings should not propagate to other classes"""
        class MomMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @mapping
            def name(self):
                pass

        class ZappMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('email')
            @mapping
            def email(self):
                pass

        self.assertEqual(
                MomMapper._map_methods,
                {'name': set(('name', 'city'))})
        self.assertEqual(
                ZappMapper._map_methods,
                {'email': set(('email',))})

    def test_mapping_decorator_cumul(self):
        """ Mappings should cumulate the ``super`` mappings
        and the local mappings """
        class FryMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @mapping
            def name(self):
                pass

        class FarnsworthMapper(FryMapper):

            _model_name = 'res.users'

            @changed_by('email')
            @mapping
            def email(self):
                pass

        self.assertEqual(
                FarnsworthMapper._map_methods,
                {'name': set(('name', 'city')),
                 'email': set(('email',))})

    def test_mapping_decorator_cumul_changed_by(self):
        """ Mappings should cumulate the changed_by fields of the
        ``super`` mappings and the local mappings """
        class FryMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @mapping
            def name(self):
                pass

        class FarnsworthMapper(FryMapper):

            _model_name = 'res.users'

            @changed_by('email')
            @mapping
            def name(self):
                pass

        self.assertEqual(
                FarnsworthMapper._map_methods,
                {'name': set(('name', 'city', 'email'))})
