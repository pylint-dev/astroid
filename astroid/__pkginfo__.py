# Copyright (c) 2006-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2014 Google, Inc.

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""astroid packaging information"""
distname = 'astroid'

modname = 'astroid'

version = '1.5.0'
numversion = tuple(map(int, version.split('.')))

extras_require = {}
install_requires = ['lazy_object_proxy', 'six', 'wrapt']
extras_require[':python_version<"3.4"'] = ['enum34', 'singledispatch']

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
