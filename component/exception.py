# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


class ComponentException(Exception):
    """ Base Exception for the components """


class NoComponentError(ComponentException):
    """ No component has been found """


class SeveralComponentError(ComponentException):
    """ More than one component have been found """
