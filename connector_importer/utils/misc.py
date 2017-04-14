# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import importlib

# http://chase-seibert.github.io/blog/2014/04/23/python-imp-examples.html


def import_klass_from_dotted_path(dotted_path, path=None):
    """Load a klass via dotted path."""

    module, klass_name = dotted_path.rsplit('.', 1)
    return getattr(importlib.import_module(module), klass_name)
