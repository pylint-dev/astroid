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
"""Python Abstract Syntax Tree New Generation

The aim of this module is to provide a common base representation of
python source code for projects such as pychecker, pyreverse,
pylint... Well, actually the development of this library is essentialy
governed by pylint's needs.

It extends class defined in the compiler.ast [1] module with some
additional methods and attributes. Instance attributes are added by a
builder object, which can either generate extended ast (let's call
them astng ;) by visiting an existant ast tree or by inspecting living
object. Methods are added by monkey patching ast classes.

Main modules are:

* nodes and scoped_nodes for more information about methods and
  attributes added to different node classes

* the manager contains a high level object to get astng trees from
  source files and living objects. It maintains a cache of previously
  constructed tree for quick access

* builder contains the class responsible to build astng trees


:author:    Sylvain Thenault
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2007 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__doctype__ = "restructuredtext en"

from logilab.common.compat import chain, imap

# WARNING: internal imports order matters !

from logilab.astng._exceptions import *



def unpack_infer(stmt, context=None):
    """return an iterator on nodes infered by the given statement
    if the infered value is a list or a tuple, recurse on it to
    get values infered by its content
    """
    if isinstance(stmt, (List, Tuple)):
        # XXX loosing context
        return chain(*imap(unpack_infer, stmt.nodes))
    infered = stmt.infer(context).next()
    if infered is stmt:
        return iter( (stmt,) )
    return chain(*imap(unpack_infer, stmt.infer(context)))

def copy_context(context):
    if context is not None:
        return context.clone()
    else:
        return InferenceContext()
    
def path_wrapper(func):
    """return the given infer function wrapped to handle the path"""
    def wrapped(node, context=None, _func=func, **kwargs):
        """wrapper function handling context"""
        if context is None:
            context = InferenceContext(node)
        context.push(node)
        yielded = []
        try:
            for res in _func(node, context, **kwargs):
                # unproxy only true instance, not const, tuple, dict...
                if res.__class__ is Instance:
                    ares = res._proxied
                else:
                    ares = res
                if not ares in yielded:
                    yield res
                    yielded.append(ares)
            context.pop()
        except:
            context.pop()
            raise
    return wrapped


# imports #####################################################################

from logilab.common.decorators import classproperty

from logilab.astng.manager import ASTNGManager, Project, Package
MANAGER = ASTNGManager()

from logilab.astng.nodes import *
from logilab.astng.scoped_nodes import *

from logilab.astng import lookup
lookup._decorate(nodes)

from logilab.astng import inference
