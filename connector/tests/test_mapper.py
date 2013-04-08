# -*- coding: utf-8 -*-

import unittest2
import mock

from openerp.addons.connector.unit.mapper import (
    Mapper,
    ImportMapper,
    MappingDefinition,
    changed_by,
    only_create,
    mapping)


class test_mapper(unittest2.TestCase):
    """ Test Mapper """

    def test_mapping_decorator(self):
        class KifKrokerMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('name', 'city')
            @mapping
            @only_create
            def name(self):
                pass

            @changed_by('email')
            @mapping
            def email(self):
                pass

            @changed_by('street')
            @mapping
            def street(self):
                pass

        self.maxDiff = None
        name_def = MappingDefinition(changed_by=set(('name', 'city')),
                                     only_create=True)
        email_def = MappingDefinition(changed_by=set(('email',)),
                                      only_create=False)
        street_def = MappingDefinition(changed_by=set(('street',)),
                                       only_create=False)

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
            @mapping
            def name(self):
                pass

        class ZappMapper(Mapper):

            _model_name = 'res.users'

            @changed_by('email')
            @only_create
            @mapping
            def email(self):
                pass

        mom_def = MappingDefinition(changed_by=set(('name', 'city')),
                                    only_create=False)
        zapp_def = MappingDefinition(changed_by=set(('email',)),
                                     only_create=True)

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
                                     only_create=False)
        email_def = MappingDefinition(changed_by=set(('email',)),
                                      only_create=False)
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
                                     only_create=False)

        self.assertEqual(FarnsworthMapper._map_methods,
                         {'name': name_def})

    def test_mapping_record(self):
        """ Map a record and check the result """
        class MyMapper(ImportMapper):

            direct = [('name', 'out_name')]

            @mapping
            def street(self, record):
                return {'out_street': record['street'].upper()}

        env = mock.MagicMock()
        record = {'name': 'Guewen',
                    'street': 'street'}
        mapper = MyMapper(env)
        mapper.convert(record)
        expected = {'out_name': 'Guewen',
                    'out_street': 'STREET'}
        self.assertEqual(mapper.data, expected)
        self.assertEqual(mapper.data_for_create, expected)

    def test_mapping_record_on_create(self):
        """ Map a record and check the result for creation of record """
        class MyMapper(ImportMapper):

            direct = [('name', 'out_name')]

            @mapping
            def street(self, record):
                return {'out_street': record['street'].upper()}

            @only_create
            @mapping
            def city(self, record):
                return {'out_city': 'city'}

        env = mock.MagicMock()
        record = {'name': 'Guewen',
                  'street': 'street'}
        mapper = MyMapper(env)
        mapper.convert(record)
        expected = {'out_name': 'Guewen',
                    'out_street': 'STREET'}
        self.assertEqual(mapper.data, expected)
        expected = {'out_name': 'Guewen',
                    'out_street': 'STREET',
                    'out_city': 'city'}
        self.assertEqual(mapper.data_for_create, expected)

    def test_mapping_record_children(self):
        """ Map a record with children and check the result """

        class LineMapper(ImportMapper):
            direct = [('name', 'name')]

            @mapping
            def price(self, record):
                return {'price': record['price'] * 2}

            @only_create
            @mapping
            def discount(self, record):
                return {'discount': .5}

        class SaleMapper(ImportMapper):

            direct = [('name', 'name')]

            children = [('lines', 'line_ids', 'sale.order.line')]

            def _init_child_mapper(self, model_name):
                return LineMapper(self.environment)

        env = mock.MagicMock()

        record = {'name': 'SO1',
                  'lines': [{'name': 'Mango',
                             'price': 10},
                            {'name': 'Pumpkin',
                             'price': 20}]}
        mapper = SaleMapper(env)
        mapper.convert(record)
        expected = {'name': 'SO1',
                    'line_ids': [(0, 0, {'name': 'Mango',
                                         'price': 20}),
                                 (0, 0, {'name': 'Pumpkin',
                                         'price': 40})]
                    }
        self.assertEqual(mapper.data, expected)
        expected = {'name': 'SO1',
                    'line_ids': [(0, 0, {'name': 'Mango',
                                         'price': 20,
                                         'discount': .5}),
                                 (0, 0, {'name': 'Pumpkin',
                                         'price': 40,
                                         'discount': .5})]
                    }
        self.assertEqual(mapper.data_for_create, expected)
