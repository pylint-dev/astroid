#!/usr/bin/env python
# pylint: disable=W0404,W0622,W0704,W0613
# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option) any
# later version.
#
# astroid is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid.  If not, see <http://www.gnu.org/licenses/>.
"""Generic Setup script, takes package info from __pkginfo__.py file.
"""
__docformat__ = "restructuredtext en"

import os
import sys
from os.path import isdir, exists, join

from setuptools import setup

sys.modules.pop('__pkginfo__', None)
# import optional features
__pkginfo__ = __import__("__pkginfo__")
# import required features
from __pkginfo__ import modname, version, license, description, \
    web, author, author_email

distname = getattr(__pkginfo__, 'distname', modname)
data_files = getattr(__pkginfo__, 'data_files', None)
include_dirs = getattr(__pkginfo__, 'include_dirs', [])
install_requires = getattr(__pkginfo__, 'install_requires', None)
classifiers = getattr(__pkginfo__, 'classifiers', [])

if exists('README'):
    long_description = open('README').read()
else:
    long_description = ''


def install(**kwargs):
    """setup entry point"""
    if '--force-manifest' in sys.argv:
        sys.argv.remove('--force-manifest')
    return setup(name = distname,
                 version = version,
                 license = license,
                 description = description,
                 long_description = long_description,
                 classifiers = classifiers,
                 author = author,
                 author_email = author_email,
                 url = web,
                 data_files = data_files,
                 include_package_data = True,
                 install_requires = install_requires,
                 package_dir = {modname: '.'},
                 packages = [modname],
                 package_data = {
                     '': ['brain/*.py', 
                          'test/regrtest_data/absimp/*.py', 
                          'test/regrtest_data/package/*.py',
                          'test/regrtest_data/package/subpackage/*.py',
                          'test/regrtest_data/absimp/sidepackage/*.py',
                          'test/regrtest_data/unicode_package/*.py',
                          'test/regrtest_data/unicode_package/core/*.py',
                          'test/data*/*.egg',
                          'test/data*/*.zip',
                          ],
                 },
                 **kwargs
                 )

if __name__ == '__main__' :
    install()
