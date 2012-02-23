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

from osv import osv, fields
import netsvc
from tempfile import TemporaryFile
from ftplib import FTP
import sys
import os
import shutil

class FileConnection(object):

    def is_(self, protocole):
        return self.protocole.lower() == protocole

    def __init__(self, protocole, location, user, pwd):
        self.protocole = protocole
        if self.is_('ftp'):
            self.connection = FTP(location)
            self.connection .login(user, pwd)

    def send(self, filepath, filename, output_file, create_patch=None):
        if self.is_('ftp'):
            self.connection.cwd(filepath)
            self.connection.storbinary('STOR ' + filename, output_file)
            output_file.close()
            return True
        elif self.is_('filestore'):
            output = open(os.path.join(filepath, filename), 'w+b')
            for line in output_file.readlines():
                output.write(line)
            output.close()
            output_file.close()
            return True

    def get(self, filepath, filename):
        if self.is_('ftp'):
            outfile = TemporaryFile('w+b')
            self.connection.cwd('/') #go to root menu by security
            self.connection.cwd(filepath)
            self.connection.retrbinary("RETR " + filename, outfile.write)
            outfile.seek(0)
            return outfile
        if self.is_('filestore'):
            return open(os.path.join(filepath, filename), 'w+b')

    def search(self, filepath, filename):
        if self.is_('ftp'):
            self.connection.cwd('/') #go to root menu by security
            self.connection.cwd(filepath)
            return [x for x in self.connection.nlst() if filename.encode('utf-8') in x]
        if self.is_('filestore'):
            return [x for x in os.listdir(filepath) if filename.encode('utf-8') in x]


