# -*- coding: utf-8 -*-

import unittest2
import mock
import openerp.tests.common as common

from openerp.addons.connector.unit.mapper import (
    Mapper,
    ImportMapper,
    MappingDefinition,
    changed_by,
    only_create,
    convert,
    m2o_to_backend,
    backend_to_m2o,
    none,
    mapping)

from openerp.addons.connector.backend import Backend
from openerp.addons.connector.connector import Environment
from openerp.addons.connector.session import ConnectorSession


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
        map_record = mapper.map_record(record)
        expected = {'out_name': 'Guewen',
                    'out_street': 'STREET'}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(only_create=True), expected)

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
        map_record = mapper.map_record(record)
        expected = {'out_name': 'Guewen',
                    'out_street': 'STREET'}
        self.assertEqual(map_record.values(), expected)
        expected = {'out_name': 'Guewen',
                    'out_street': 'STREET',
                    'out_city': 'city'}
        self.assertEqual(map_record.values(only_create=True), expected)

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
        map_record = mapper.map_record(record)
        expected = {'name': 'SO1',
                    'line_ids': [(0, 0, {'name': 'Mango',
                                         'price': 20}),
                                 (0, 0, {'name': 'Pumpkin',
                                         'price': 40})]
                    }
        self.assertEqual(map_record.values(), expected)
        expected = {'name': 'SO1',
                    'line_ids': [(0, 0, {'name': 'Mango',
                                         'price': 20,
                                         'discount': .5}),
                                 (0, 0, {'name': 'Pumpkin',
                                         'price': 40,
                                         'discount': .5})]
                    }
        self.assertEqual(map_record.values(only_create=True), expected)

    def test_mapping_modifier(self):
        """ Map a direct record with a modifier function """

        def do_nothing(field):
            def transform(self, record, to_attr):
                return record[field]
            return transform

        class MyMapper(ImportMapper):
            direct = [(do_nothing('name'), 'out_name')]

        env = mock.MagicMock()
        record = {'name': 'Guewen'}
        mapper = MyMapper(env)
        map_record = mapper.map_record(record)
        expected = {'out_name': 'Guewen'}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(only_create=True), expected)

    def test_mapping_convert(self):
        """ Map a direct record with the convert modifier function """
        class MyMapper(ImportMapper):
            direct = [(convert('name', int), 'out_name')]

        env = mock.MagicMock()
        record = {'name': '300'}
        mapper = MyMapper(env)
        map_record = mapper.map_record(record)
        expected = {'out_name': 300}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(only_create=True), expected)

    def test_mapping_modifier_none(self):
        """ Pipeline of modifiers """
        class MyMapper(ImportMapper):
            direct = [(none('in_f'), 'out_f'),
                      (none('in_t'), 'out_t')]

        env = mock.MagicMock()
        record = {'in_f': False, 'in_t': True}
        mapper = MyMapper(env)
        map_record = mapper.map_record(record)
        expected = {'out_f': None, 'out_t': True}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(only_create=True), expected)

    def test_mapping_modifier_pipeline(self):
        """ Pipeline of modifiers """
        class MyMapper(ImportMapper):
            direct = [(none(convert('in_f', bool)), 'out_f'),
                      (none(convert('in_t', bool)), 'out_t')]

        env = mock.MagicMock()
        record = {'in_f': 0, 'in_t': 1}
        mapper = MyMapper(env)
        map_record = mapper.map_record(record)
        expected = {'out_f': None, 'out_t': True}
        self.assertEqual(map_record.values(), expected)
        self.assertEqual(map_record.values(only_create=True), expected)


class test_mapper_binding(common.TransactionCase):
    """ Test Mapper with Bindings"""

    def setUp(self):
        super(test_mapper_binding, self).setUp()
        self.session = ConnectorSession(self.cr, self.uid)
        self.Partner = self.registry('res.partner')
        self.backend = mock.Mock(wraps=Backend('x', version='y'),
                                 name='backend')
        backend_record = mock.Mock()
        backend_record.get_backend.return_value = self.backend
        self.env = Environment(backend_record, self.session, 'res.partner')
        self.country_binder = mock.Mock(name='country_binder')
        self.country_binder.return_value = self.country_binder
        self.backend.get_class.return_value = self.country_binder

    def test_mapping_m2o_to_backend(self):
        """ Map a direct record with the m2o_to_backend modifier function """
        class MyMapper(ImportMapper):
            _model_name = 'res.partner'
            direct = [(m2o_to_backend('country_id'), 'country')]

        partner_id = self.ref('base.main_partner')
        self.Partner.write(self.cr, self.uid, partner_id,
                           {'country_id': self.ref('base.ch')})
        partner = self.Partner.browse(self.cr, self.uid, partner_id)
        self.country_binder.to_backend.return_value = 10

        mapper = MyMapper(self.env)
        map_record = mapper.map_record(partner)
        self.assertEqual(map_record.values(), {'country': 10})
        self.country_binder.to_backend.assert_called_once_with(
            partner.country_id.id, wrap=False)

    def test_mapping_backend_to_m2o(self):
        """ Map a direct record with the backend_to_m2o modifier function """
        class MyMapper(ImportMapper):
            _model_name = 'res.partner'
            direct = [(backend_to_m2o('country'), 'country_id')]

        record = {'country': 10}
        self.country_binder.to_openerp.return_value = 44
        mapper = MyMapper(self.env)
        map_record = mapper.map_record(record)
        self.assertEqual(map_record.values(), {'country_id': 44})
        self.country_binder.to_openerp.assert_called_once_with(
            10, unwrap=False)
