# -*- coding: utf-8 -*-
# Author: Simone Orsi
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import csv
import base64
import time
from chardet.universaldetector import UniversalDetector

from cStringIO import StringIO

from ..log import logger


def get_encoding(data):
    """ try to get encoding incrementally
    see http://chardet.readthedocs.org/en/latest/usage.html
    #example-detecting-encoding-incrementally
    """
    start = time.time()
    msg = 'detecting file encoding...'
    logger.info(msg)
    file_like = StringIO(data)
    detector = UniversalDetector()
    for i, line in enumerate(file_like):
        detector.feed(line)
        if detector.done:
            break
    detector.close()
    msg = 'encoding found in %s sec' % str(time.time() - start)
    msg += str(detector.result)
    logger.info(msg)
    return detector.result


def csv_content_to_file(data):
    """ odoo binary fields spit out b64 data
    """
    # guess encoding via chardet (LOVE IT! :))
    encoding_info = get_encoding(data)
    encoding = encoding_info['encoding']
    if encoding is None or encoding != 'utf-8':
        try:
            data_str = data.decode(encoding)
        except (UnicodeDecodeError, TypeError):
            # dirty fallback in case
            # we don't spot the right encoding above
            for enc in ('utf-16le', 'latin-1', 'ascii', ):
                try:
                    data_str = data.decode(enc)
                    break
                except UnicodeDecodeError:
                    data_str = data
        data_str = data_str.encode('utf-8')
    else:
        data_str = data
    return StringIO(data_str)


def read_path(path):
    with file(path, 'r') as thefile:
        return thefile.read()


class CSVReader(object):

    def __init__(self,
                 filepath=None,
                 filedata=None,
                 delimiter='|',
                 quotechar='"',
                 fieldnames=None):
        assert filedata or filepath, 'Provide a file path or some file data!'
        if filepath:
            filedata = read_path(filepath)
        else:
            filedata = base64.decodestring(filedata)
        # remove NULL byte
        filedata = filedata.replace('\x00', '')
        self.data = csv_content_to_file(filedata)
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.fieldnames = fieldnames

    def read_lines(self):
        """ return iterator that yields lines
        and add info to them (like line nr).
        """
        self.data.seek(0)
        reader = csv.DictReader(
            self.data,
            delimiter=str(self.delimiter),
            quotechar=str(self.quotechar),
            fieldnames=self.fieldnames,
        )
        for line in reader:
            line['_line_nr'] = reader.line_num
            yield line


def gen_chunks(iterable, chunksize=10):
    """Chunk generator.

    Take an iterable and yield `chunksize` sized slices.
    """
    chunk = []
    for i, line in enumerate(iterable):
        if (i % chunksize == 0 and i > 0):
            yield chunk
            del chunk[:]
        chunk.append(line)
    yield chunk
