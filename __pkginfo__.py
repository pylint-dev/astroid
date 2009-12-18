# Copyright (c) 2003-2009 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""
logilab.astng packaging information
"""

distname = 'logilab-astng'

modname = 'astng'
subpackage_of = 'logilab'

numversion = (0, 19, 2)
version = '.'.join([str(num) for num in numversion])

install_requires = ['logilab-common >= 0.39.0']

pyversions = ["2.3", "2.4", "2.5", '2.6']

license = 'GPL'

author = 'Logilab'
author_email = 'python-projects@lists.logilab.org'
mailinglist = "mailto://%s" % author_email
web = "http://www.logilab.org/project/%s" % distname
ftp = "ftp://ftp.logilab.org/pub/%s" % modname

short_desc = "extend python's abstract syntax tree"

long_desc = """The aim of this module is to provide a common base \
representation of
python source code for projects such as pychecker, pyreverse,
pylint... Well, actually the development of this library is essentialy
governed by pylint's needs.

It extends class defined in the compiler.ast [1] module (python <= 2.4) or in
the builtin _ast module (python >= 2.5) with some additional methods and
attributes. Instance attributes are added by a builder object, which can either
generate extended ast (let's call them astng ;) by visiting an existant ast
tree or by inspecting living object. Methods are added by monkey patching ast
classes."""


from os.path import join
include_dirs = [join('test', 'regrtest_data'),
                join('test', 'data'), join('test', 'data2')]
