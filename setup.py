#!/usr/bin/env python
# Copyright (c) 2006, 2009-2013 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

# pylint: disable=W0404,W0622,W0704,W0613
"""Setup script for astroid."""
import os
from setuptools import setup, find_packages
from setuptools.command import easy_install
from setuptools.command import install_lib


real_path = os.path.realpath(__file__)
astroid_dir = os.path.dirname(real_path)
pkginfo = os.path.join(astroid_dir, 'astroid', '__pkginfo__.py')

with open(pkginfo, 'rb') as fobj:
    exec(compile(fobj.read(), pkginfo, 'exec'), locals())

with open(os.path.join(astroid_dir, 'README.rst')) as fobj:
    long_description = fobj.read()

class AstroidInstallLib(install_lib.install_lib):
    def byte_compile(self, files):
        test_datadir = os.path.join('astroid', 'tests', 'testdata')
        files = [f for f in files if test_datadir not in f]
        install_lib.install_lib.byte_compile(self, files)


class AstroidEasyInstallLib(easy_install.easy_install):
    # override this since pip/easy_install attempt to byte compile
    # test data files, some of them being syntactically wrong by design,
    # and this scares the end-user
    def byte_compile(self, files):
        test_datadir = os.path.join('astroid', 'tests', 'testdata')
        files = [f for f in files if test_datadir not in f]
        easy_install.easy_install.byte_compile(self, files)


def install():
    return setup(name = distname,
                 version = version,
                 license = license,
                 description = description,
                 long_description = long_description,
                 classifiers = classifiers,
                 author = author,
                 author_email = author_email,
                 url = web,
                 include_package_data = True,
                 install_requires = install_requires,
                 extras_require=extras_require,
                 packages = find_packages(),
                 cmdclass={'install_lib': AstroidInstallLib,
                           'easy_install': AstroidEasyInstallLib}
                 )


if __name__ == '__main__' :
    install()
