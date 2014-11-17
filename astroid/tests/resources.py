# Copyright 2014 Google, Inc. All rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
import os
import sys

import pkg_resources

from astroid import builder


DATA_DIR = 'testdata/python{}/'.format(sys.version_info[0])

def find(name):
    return pkg_resources.resource_filename(
        'astroid.tests', os.path.normpath(os.path.join(DATA_DIR, name)))


def build_file(path, modname=None):
     return builder.AstroidBuilder().file_build(find(path), modname)


class SysPathSetup(object):
    def setUp(self):
        sys.path.insert(0, find(''))

    def tearDown(self):
        del sys.path[0]
        datadir = find('')
        for key in list(sys.path_importer_cache):
            if key.startswith(datadir):
                del sys.path_importer_cache[key]


