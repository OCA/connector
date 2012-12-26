# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
#   base_file_protocole for OpenERP                                           #
#   Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>  #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU Affero General Public License as            #
#   published by the Free Software Foundation, either version 3 of the        #
#   License, or (at your option) any later version.                           #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU Affero General Public License for more details.                       #
#                                                                             #
#   You should have received a copy of the GNU Affero General Public License  #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################

from tempfile import TemporaryFile
import ftplib
import os
import csv
import paramiko
import errno
import functools
import logging

_logger = logging.getLogger(__name__)
try:
    import xlrd
except ImportError:
    _logger.warning('You must install xlrd, if you need to read xls file')

def open_and_close_connection(func):
    """
    Open And Close Decorator will automatically launch the connection
    to the external storage system.
    Then the function is excecuted and the connection is closed
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.persistant:
            if not self.connection:
                self.connect()
            return func(self, *args, **kwargs)
        else:
            self.connect()
            try:
                response = func(self, *args, **kwargs)
            except:
                raise
            finally:
                self.close()
            return response
    return wrapper

# Extend paramiko lib with the method mkdirs
def stfp_mkdirs(self, path, mode=511):
    try:
        self.stat(path)
    except IOError, e:
        if e.errno == errno.ENOENT:
            try:
                self.mkdir(path, mode)
            except IOError, e:
                if e.errno == errno.ENOENT:
                    self.mkdirs(os.path.dirname(path), mode)
                    self.mkdir(path, mode)
                else:
                    raise
paramiko.SFTPClient.mkdirs = stfp_mkdirs

# Extend ftplib with the method mkdirs
def ftp_mkdirs(self, path):
    current_dir = self.pwd()
    try:
        self.cwd(path)
    except ftplib.error_perm, e:
        if "550" in str(e):
            try:
                self.mkd(path)
            except ftplib.error_perm, e:
                if "550" in str(e):
                    self.mkdirs(os.path.dirname(path))
                    self.mkd(path)
                else:
                    raise
    self.cwd(current_dir)
ftplib.FTP.mkdirs = ftp_mkdirs


class FileConnection(object):

    def is_(self, protocole):
        return self.protocole.lower() == protocole

    def __init__(self, protocole, location, user, pwd, port=None, allow_dir_creation=None, home_folder='/', persistant=False):
        self.protocole = protocole
        self.allow_dir_creation = allow_dir_creation
        self.location = location
        self.home_folder = home_folder or '/'
        self.port = port
        self.user = user
        self.pwd = pwd
        self.connection = None
        self.persistant = False

    def connect(self):
        if self.is_('ftp'):
            self.connection = ftplib.FTP(self.location)
            self.connection.login(self.user, self.pwd)
        elif self.is_('sftp'):
            transport = paramiko.Transport((self.location, self.port or 22))
            transport.connect(username = self.user, password = self.pwd)
            self.connection = paramiko.SFTPClient.from_transport(transport)

    def close(self):
        if self.is_('ftp') or self.is_('sftp') and self.connection is not None:
            self.connection.close()

    @open_and_close_connection
    def send(self, filepath, filename, output_file, create_patch=None):
        if self.is_('ftp'):
            filepath = os.path.join(self.home_folder, filepath)
            if self.allow_dir_creation:
                self.connection.mkdirs(filepath)
            self.connection.cwd(filepath)
            self.connection.storbinary('STOR ' + filename, output_file)
            output_file.close()
            return True
        elif self.is_('filestore'):
            if not os.path.isabs(filepath):
                filepath = os.path.join(self.location, filepath)
            if self.allow_dir_creation and not os.path.exists(filepath):
                os.makedirs(filepath)
            output = open(os.path.join(filepath, filename), 'w+b')
            for line in output_file.readlines():
                output.write(line)
            output.close()
            output_file.close()
            return True
        elif self.is_('sftp'):
            if not os.path.isabs(filepath):
                filepath = os.path.join(self.home_folder, filepath)
            if self.allow_dir_creation:
                self.connection.mkdirs(filepath)
            output = self.connection.open(os.path.join(filepath, filename), 'w+b')
            for line in output_file.readlines():
                output.write(line)
            output.close()
            output_file.close()
            return True

    @open_and_close_connection
    def get(self, filepath, filename):
        if self.is_('ftp'):
            outfile = TemporaryFile('w+b')
            self.connection.cwd(filepath)
            self.connection.retrbinary("RETR " + filename, outfile.write)
            outfile.seek(0)
            return outfile
        elif self.is_('filestore'):
            return open(os.path.join(filepath, filename), 'r+b')

    @open_and_close_connection
    def search(self, filepath, filename):
        if self.is_('ftp'):
            self.connection.cwd(filepath)
            #Take care that ftp lib use utf-8 and not unicode
            return [x for x in self.connection.nlst() if filename.encode('utf-8') in x]
        elif self.is_('filestore'):
            return [x for x in os.listdir(filepath) if filename in x]

    @open_and_close_connection
    def move(self, oldfilepath, newfilepath, filename):
        if self.is_('ftp'):
            self.connection.rename(os.path.join(oldfilepath, filename), os.path.join(newfilepath, filename))
        elif self.is_('filestore'):
            os.rename(os.path.join(oldfilepath, filename), os.path.join(newfilepath, filename))

class FileCsvReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, encoding="utf-8", **kwds):
        self.encoding = encoding
        self.reader = csv.DictReader(f, **kwds)

    def next(self):
        row = self.reader.next()
        res = {}
        for key, value in row.items():
            if not isinstance(key, unicode) and key:
                key = unicode(key, self.encoding)
            if not isinstance(value, unicode) and value:
                value = unicode(value, self.encoding)
            res[key] = value
        return res

    def __iter__(self):
        return self

    def reorganize(self, field_structure=None, merge_keys=None, ref_field=None):
        """
        Function to reorganize the resource from the csv. It uses the mapping (field_structure)
        to deal with the different architecture of an object (sale order with sale order line ...)
        the ref_field is used to merge the different lines (sale order with several sale order lines)
        """
        result_merge = {}
        result = []
        for line in self:
            line_tmp = line.copy()
            for child, parent in field_structure:
                if not parent in line:
                    line[parent] = {}
                if line.get(child) or line_tmp.get(child):
                    line[parent][child] = line.get(child) or line_tmp.get(child)
                    if line.get(child):
                        del line[child]
            if ref_field:
                if line[ref_field] in result_merge:
                    for key in merge_keys:
                        result_merge[line[ref_field]][key].append(line[key])
                else:
                    result_merge[line[ref_field]] = line
                    for key in merge_keys:
                        result_merge[line[ref_field]][key] =  [result_merge[line[ref_field]][key]]
            else:
                result.append(line)
        if ref_field:
            return [result_merge[key] for key in result_merge]
        else:
            return result

class FileCsvWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, fieldnames, encoding="utf-8", writeheader=False, **kwds):
        self.encoding = encoding
        if not kwds.get('dialect'):
            kwds['dialect'] = 'UNIX'
        self.writer = csv.DictWriter(f, fieldnames, **kwds)
        if writeheader:
            row = {}
            for field in fieldnames:
                row[field] = field.encode(self.encoding)
            self.writer.writerow(row)

    def writerow(self, row):
        write_row = {}
        for k,v in row.items():
            if isinstance(v, unicode) and v!=False:
                write_row[k] = v.encode(self.encoding)
            else:
                write_row[k] = v
        self.writer.writerow(write_row)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class FileXlsReader(object):

    def __init__(self, file_contents):
        self.file_contents = file_contents

    def read(self):
        wb = xlrd.open_workbook(file_contents=self.file_contents)
        sheet_name = wb.sheet_names()[0]
        sh = wb.sheet_by_name(sheet_name)
        header = sh.row_values(0)
        result = []
        for rownum in range(1, sh.nrows):
            row = {}
            index = 0
            for val in sh.row_values(rownum):
                row[header[index]] = val
                index += 1
            result.append(row)
        return result



