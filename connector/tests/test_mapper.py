# -*- coding: utf-8 -*-

import unittest2
import mock

from openerp.addons.connector.unit.mapper import (
    Mapper,
    MappingDefinition,
    changed_by,
    on_create,
    on_update,
    mapping)


class test_mapper(unittest2.TestCase):
    """ Test Mapper """

    def test_mapping_decorator(self):
        class KifKrokerMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @mapping
            @on_create
            def name(self):
                pass

            @changed_by('email')
            @mapping
            @on_update
            def email(self):
                pass

            @changed_by('street')
            @mapping
            def street(self):
                pass

        self.maxDiff = None
        name_def = MappingDefinition(changed_by=set(('name', 'city')),
                                     on_create=True,
                                     on_update=False)
        email_def = MappingDefinition(changed_by=set(('email',)),
                                      on_create=False,
                                      on_update=True)
        street_def = MappingDefinition(changed_by=set(('street',)),
                                       on_create=True,
                                       on_update=True)

        self.assertEqual(KifKrokerMapper._map_methods,
                         {'name': name_def,
                          'email': email_def,
                          'street': street_def,
                          })

    def test_mapping_decorator_cross_classes(self):
        """ Mappings should not propagate to other classes"""
        class MomMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @on_update
            @mapping
            def name(self):
                pass

        class ZappMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('email')
            @mapping
            def email(self):
                pass

        mom_def = MappingDefinition(changed_by=set(('name', 'city')),
                                    on_create=False,
                                    on_update=True)
        zapp_def = MappingDefinition(changed_by=set(('email',)),
                                     on_create=True,
                                     on_update=True)

        self.assertEqual(MomMapper._map_methods,
                         {'name': mom_def})
        self.assertEqual(ZappMapper._map_methods,
                         {'email': zapp_def})

    def test_mapping_decorator_cumul(self):
        """ Mappings should cumulate the ``super`` mappings
        and the local mappings."""
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

        name_def = MappingDefinition(changed_by=set(('name', 'city')),
                                     on_create=True,
                                     on_update=True)
        email_def = MappingDefinition(changed_by=set(('email',)),
                                      on_create=True,
                                      on_update=True)
        self.assertEqual(FarnsworthMapper._map_methods,
                         {'name': name_def,
                          'email': email_def})

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

        name_def = MappingDefinition(changed_by=set(('name', 'city', 'email')),
                                     on_create=True,
                                     on_update=True)

        self.assertEqual(FarnsworthMapper._map_methods,
                         {'name': name_def})
