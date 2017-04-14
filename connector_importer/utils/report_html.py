# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

EXAMPLEDATA = {
    "last_summary": {
        "updated": 0, "skipped": 584, "errors": 0, "created": 414
    },
    "errors": [],
    "last_start": "08/03/2017 13:46",
    "skipped": [
        {"model": "product.template",
         "line": 3,
         "message": "ALREADY EXISTS code: 8482",
         "odoo_record": 6171},
        {"model": "product.template",
         "line": 4,
         "message": "ALREADY EXISTS code: 8482",
         "odoo_record": 6171},
        {"model": "product.template",
         "line": 5,
         "message": "ALREADY EXISTS code: 8482",
         "odoo_record": 6171},
    ],
}
JSONDATA = json.dumps(EXAMPLEDATA)


def link_record(record_id, model='', record=None,
                name_field='name', target='_new'):
    """Link an existing odoo record."""
    name = 'View'
    if record:
        default = getattr(record, '_rec_name', 'Unknown')
        name = getattr(record, name_field, default)
        model = record._name
    link = (
        """<a target="{target}" """
        """href="/web?#id={id}&view_type=form&model={model}">{name}</a>"""
    ).format(
        id=record_id,
        model=model,
        name=name,
        target=target,
    )
    return link


class Reporter(object):
    """Produce a formatted HTML report from importer json data."""

    def __init__(self, jsondata, detailed=False, full_url=''):
        self._jsondata = jsondata
        self._data = json.loads(self._jsondata)
        self._html = []
        self._detailed = detailed
        self._full_url = full_url

    def html(self, wrapped=True):
        """Return HTML report."""
        self._produce()
        content = ''.join(self._html)
        if wrapped:
            return self._wrap(
                'html', self._wrap('body', content)
            )
        return content

    def _add(self, el):
        self._html.append(el)

    def _wrap(self, tag, content):
        return '<{tag}>{content}</{tag}>'.format(tag=tag, content=content)

    def _line(self, content):
        return self._wrap('p', content)

    def _value(self, key, value):
        return self._wrap('strong', key.capitalize() + ': ') + str(value)

    def _value_line(self, key, value):
        return self._line(
            self._value(key, value)
        )

    def _line_to_msg(self, line):
        res = []
        if line.get('line'):
            res.append('CSV line: {}, '.format(line['line']))
        if line.get('message'):
            res.append(line['message'])
        if 'odoo_record' in line and 'model' in line:
            res.append(
                link_record(line['odoo_record'], model=line['model'])
            )
        return ' '.join(res)

    def _listing(self, lines, list_type='ol'):
        _lines = []
        for line in lines:
            _lines.append(self._wrap('li', self._line_to_msg(line)))
        return self._wrap(
            list_type, ''.join(_lines)
        )

    def _produce(self):
        if not self._data.get('last_summary'):
            return
        # header
        self._add(self._wrap('h2', 'Last summary'))
        # start date
        self._add(self._value_line('Last start', self._data['last_start']))
        # global counters
        summary_items = self._data['last_summary'].items()
        for key, value in summary_items:
            last = key == summary_items[-1][0]
            self._add(self._value(key, value) + (' - ' if not last else ''))
        if self._detailed:
            self._add(self._wrap('h3', 'Details'))
            if self._data['skipped']:
                self._add(self._wrap('h4', 'Skipped'))
                # skip messages
                self._add(self._listing(self._data['skipped']))
            if self._data['errors']:
                self._add(self._wrap('h4', 'Errors'))
                # skip messages
                self._add(self._listing(self._data['errors']))
        if self._full_url:
            link = (
                '<a href="{}" target="_new">View full report</a>'
            ).format(self._full_url)
            self._add(self._line(link))


if __name__ == '__main__':
    reporter = Reporter(JSONDATA, detailed=1)
    print reporter.html()
