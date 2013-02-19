# -*- coding: utf-8 -*-

import unittest2
import mock

from openerp.addons.connector import (
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

        self.assertItemsEqual(
                KifKroker.map_methods,
                [(KifKroker.name, ('name', 'city')),
                 (KifKroker.email, ('email',))])

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

        ref = session = mock.Mock()
        mom_mapper = MomMapper(ref, session)
        zapp_mapper = ZappMapper(ref, session)
        self.assertItemsEqual(
                mom_mapper.map_methods,
                [(MomMapper.name, ('name', 'city'))])
        self.assertItemsEqual(
                zapp_mapper.map_methods,
                [(ZappMapper.email, ('email'))])

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

        self.assertItemsEqual(
                FarnsworthMapper.map_methods,
                [(FarnsworthMapper.name, ('name', 'city')),
                 (FarnsworthMapper.email, ('email',))])
