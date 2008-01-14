# pylint: disable-msg=W0622
#
# Copyright (c) 2003-2008 LOGILAB S.A. (Paris, FRANCE).
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

modname = 'astng'
distname = 'logilab-astng'
numversion = (0, 17, 2)
version = '.'.join([str(num) for num in numversion])
pyversions = ["2.3", "2.4", "2.5"]

license = 'GPL'
copyright = '''Copyright (c) 2003-2008 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr'''

author = 'Sylvain Thenault'
author_email = 'sylvain.thenault@logilab.fr'

short_desc = "extend python's abstract syntax tree"

long_desc = """The aim of this module is to provide a common base \
representation of
python source code for projects such as pychecker, pyreverse,
pylint... Well, actually the development of this library is essentialy
governed by pylint's needs.

It extends class defined in the compiler.ast [1] module with some
additional methods and attributes. Instance attributes are added by a
builder object, which can either generate extended ast (let's call
them astng ;) by visiting an existant ast tree or by inspecting living
object. Methods are added by monkey patching ast classes."""


web = "http://www.logilab.org/project/name/%s" % distname
ftp = "ftp://ftp.logilab.org/pub/%s" % modname
mailinglist = "mailto://python-projects@lists.logilab.org"

subpackage_of = 'logilab'

from os.path import join
include_dirs = [join('test', 'regrtest_data'),
                join('test', 'data'), join('test', 'data2')]

debian_uploader = 'Alexandre Fayolle <afayolle@debian.org>'
