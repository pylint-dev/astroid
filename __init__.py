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


:version:   $Revision: 1.24 $  
:author:    Sylvain Thenault
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2006 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__revision__ = "$Id: __init__.py,v 1.24 2006-04-20 07:37:28 syt Exp $"
__doctype__ = "restructuredtext en"

from logilab.common.compat import chain, imap

# WARNING: internal imports order matters !

from logilab.astng._exceptions import *


def unpack_infer(stmt, path=None):
    """return an iterator on nodes infered by the given statement
    if the infered value is a list or a tuple, recurse on it to
    get values infered by its content
    """
    if isinstance(stmt, (List, Tuple)):
        return chain(*imap(unpack_infer, stmt.nodes))
    infered = stmt.infer(path=path).next()
    if infered is stmt:
        return iter( (stmt,) )
    return chain(*imap(unpack_infer, stmt.infer(path=path)))

def _infer_stmts(stmts, name=None, path=None, frame=None):
    """return an iterator on statements infered by each statement in <stmts>
    """
    stmt = None
    one_infered = False
    for stmt in stmts:
        if stmt is YES:
            yield stmt
            one_infered = True
            continue
        try:
            for infered in stmt.infer(stmt._infer_name(frame, name), path):
                yield infered
                one_infered = True
        except UnresolvableName:
            continue
        except InferenceError:
            yield YES
            one_infered = True
    if not one_infered:
        raise InferenceError(str(stmt))

# special inference objects ###################################################

class Yes(object):
    """a yes object"""
    def __str__(self):
        return 'YES'
    def __getattribute__(self, name):
        return self
    def __call__(self, *args, **kwargs):
        return self
YES = Yes()

class Proxy:
    """a simple proxy object"""
    def __init__(self, proxied):
        self._proxied = proxied

    def __getattr__(self, name):
        return getattr(self._proxied, name)

    def infer(self, name=None, path=None):
        yield self

class Instance(Proxy):
    """a special node representing a class instance"""
    def getattr(self, name, path=None, lookupclass=True):
        try:
            return self._proxied.instance_attr(name, path)
        except NotFoundError:
            if name == '__class__':
                return [self._proxied]
            if name == '__name__':
                # access to __name__ gives undefined member on class
                # instances but not on class objects
                raise NotFoundError(name)
            if lookupclass:
                return self._proxied.getattr(name, path)
        raise NotFoundError(name)

    def igetattr(self, name, path=None):
        """infered getattr"""
        try:
            # XXX frame should be self._proxied, or not ?
            return _infer_stmts(self.getattr(name, path, lookupclass=False), name,
                                frame=self, path=path)
        except NotFoundError:
            try:
                # fallback to class'igetattr since it has some logic to handle
                # descriptors
                return self._proxied.igetattr(name, path=path)
            except NotFoundError:
                raise InferenceError(name)
        
    def infer_call_result(self, caller, inf_path=None):
        """infer what's a class instance is returning when called"""
        one_infered = False
        for node in self._proxied.igetattr('__call__', inf_path):
            for res in node.infer_call_result(caller, inf_path):
                one_infered = True
                yield res
        if not one_infered:
            raise InferenceError()

    def __repr__(self):
        return 'Instance of %s' % self._proxied.name

    def callable(self):
        try:
            self._proxied.getattr('__call__')
            return True
        except NotFoundError:
            return False
        
class Generator(Proxy): 
    """a special node representing a generator"""
    def callable(self):
        return True

# imports #####################################################################

from logilab.astng.manager import ASTNGManager, Project, Package
MANAGER = ASTNGManager()

from logilab.astng.nodes import *
from logilab.astng import nodes
from logilab.astng.scoped_nodes import *
from logilab.astng import inference
from logilab.astng import lookup
lookup._decorate(nodes)

List._proxied = MANAGER.astng_from_class(list)
List.__bases__ += (inference.Instance,)
Tuple._proxied = MANAGER.astng_from_class(tuple)
Tuple.__bases__ += (inference.Instance,)
Dict._proxied = MANAGER.astng_from_class(dict)
Dict.__bases__ += (inference.Instance,)
Dict._proxied = MANAGER.astng_from_class(dict)

builtin_astng = Dict._proxied.root()

Const.__bases__ += (inference.Instance,)
Const._proxied = None
def Const___getattr__(self, name):
    if self.value is None:
        raise AttributeError(name)
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return getattr(self._proxied, name)
Const.__getattr__ = Const___getattr__
def Const_getattr(self, name, path=None, lookupclass=None):
    if self.value is None:
        raise NotFoundError(name)
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return self._proxied.getattr(name, path)
Const.getattr = Const_getattr
