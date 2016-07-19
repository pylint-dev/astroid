# Copyright (c) 2006-2016 LOGILAB S.A. (Paris, FRANCE)
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""astroid packaging information"""
import sys

distname = 'astroid'

modname = 'astroid'

numversion = (1, 5, 0)
version = '.'.join([str(num) for num in numversion])

install_requires = ['lazy_object_proxy', 'six', 'wrapt']

if sys.version_info < (3, 4):
    install_requires += ['enum34', 'singledispatch']

# pylint: disable=redefined-builtin; why license is a builtin anyway?
license = 'LGPL'

author = 'Python Code Quality Authority'
author_email = 'code-quality@python.org'
mailinglist = "mailto://%s" % author_email
web = 'https://github.com/PyCQA/astroid'

description = "A abstract syntax tree for Python with inference support."

classifiers = ["Topic :: Software Development :: Libraries :: Python Modules",
               "Topic :: Software Development :: Quality Assurance",
               "Programming Language :: Python",
               "Programming Language :: Python :: 2",
               "Programming Language :: Python :: 3",
              ]
