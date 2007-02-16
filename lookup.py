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
"""name lookup methods, available on Name ans scoped (Module, Class,
Function...) nodes:

* .lookup(name)
* .ilookup(name)

Be careful, lookup is kinda internal and return a tuple (scope, [stmts]), while
ilookup return an iterator on infered values

:author:    Sylvain Thenault
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2007 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__docformat__ = "restructuredtext en"

import __builtin__

from logilab.astng.utils import are_exclusive
from logilab.astng import nodes, MANAGER, _infer_stmts, copy_context


def lookup(self, name):
    """lookup a variable name

    return the scoope node and the list of assignments associated to the given
    name according to the scope where it has been found (locals, globals or
    builtin)

    The lookup is starting from self's scope. If self is not a frame itself and
    the name is found in the inner frame locals, statements will be filtered
    to remove ignorable statements according to self's location
    """
    #assert ID_RGX.match(name), '%r is not a valid identifier' % name
    return self.scope().scope_lookup(self, name)

def scope_lookup(self, node, name, offset=0):
    try:
        stmts = node._filter_stmts(self.locals[name], self, offset)
    except KeyError:
        stmts = ()
    if stmts:
        return self, stmts
    if self.parent:
        # nested scope: if parent scope is a function, that's fine
        # else jump to the module
        pscope = self.parent.scope()
        if not isinstance(pscope, nodes.Function):
            pscope = pscope.root()
        return pscope.scope_lookup(node, name)
    return builtin_lookup(name)

def class_scope_lookup(self, node, name, offset=0):
    if node in self.bases:
        #print 'frame swaping'
        frame = self.parent.frame()
        # line offset to avoid that class A(A) resolve the ancestor to
        # the defined class
        offset = -1
    else:
        frame = self
    return scope_lookup(frame, node, name, offset)

def function_scope_lookup(self, node, name, offset=0):
    if node in self.defaults:
        frame = self.parent.frame()
        # line offset to avoid that def func(f=func) resolve the default
        # value to the defined function
        offset = -1
    else:
        # check this is not used in function decorators
        frame = self
    return scope_lookup(frame, node, name, offset)
    
def builtin_lookup(name):
    """lookup a name into the builtin module
    return the list of matching statements and the astng for the builtin
    module
    """
    builtinastng = MANAGER.astng_from_module(__builtin__)
    try:
        stmts = builtinastng.locals[name]
    except KeyError:
        stmts = ()
    return builtinastng, stmts

def ilookup(self, name, context=None):
    """infered lookup
    
    return an iterator on infered values of the statements returned by
    the lookup method
    """
    frame, stmts = self.lookup(name)
    context = copy_context(context)
    context.lookupname = name
    return _infer_stmts(stmts, context, frame)


def _filter_stmts(self, stmts, frame, offset):
    """filter statements:

    If self is not a frame itself and the name is found in the inner
    frame locals, statements will be filtered to remove ignorable
    statements according to self's location
    """
    # if offset == -1, my actual frame is not the inner frame but its parent
    #
    # class A(B): pass
    #
    # we need this to resolve B correctly
    if offset == -1:
        myframe = self.frame().parent.frame()
    else:
        myframe = self.frame()
    if not myframe is frame or self is frame:
        return stmts
    #print self.name, frame.name
    mystmt = self.statement()
    # line filtering if we are in the same frame
    if myframe is frame:
        mylineno = mystmt.source_line() + offset
    else:
        # disabling lineno filtering
        print 'disabling lineno filtering'
        mylineno = 0
    _stmts = []
    _stmt_parents = []
    #print '-'*60
    #print 'filtering', stmts, mylineno
    for node in stmts:
        stmt = node.statement()
        # line filtering is on and we have reached our location, break
        if mylineno > 0 and stmt.source_line() > mylineno:
            #print 'break', mylineno, stmt.source_line()
            break
        if isinstance(node, Class) and self in node.bases:
            #print 'breaking on', self, node.bases            
            break
        try:
            ass_type = node.ass_type()
            if ass_type is mystmt:
                if not isinstance(ass_type, (ListCompFor,  GenExprFor)):
                    #print 'break now2', self, ass_type
                    break
                if isinstance(self, (Const, Name)):
                    _stmts = [self]
                    #print 'break now', ass_type, self, node
                    break
        except AttributeError:
            ass_type = None
        # a loop assigment is hidding previous assigment
        if isinstance(ass_type, (For, ListCompFor,  GenExprFor)) and \
               ass_type.parent_of(self):
            _stmts = [node]
            _stmt_parents = [stmt.parent]
            continue
        try:
            pindex = _stmt_parents.index(stmt.parent)
        except ValueError:
            pass
        else:
            try:
                if ass_type and _stmts[pindex].ass_type().parent_of(ass_type):
                    # print 'skipping', node, node.source_line()
                    continue
            except AttributeError:
                pass # name from Import, Function, Class...
            if not are_exclusive(self, node):
                ###print 'PARENT', stmt.parent
                #print 'removing', _stmts[pindex]
                del _stmt_parents[pindex]
                del _stmts[pindex]
        if isinstance(node, AssName):
            if stmt.parent is mystmt.parent:
                #print 'assign clear'
                _stmts = []
                _stmt_parents = []
            if node.flags == 'OP_DELETE':
                #print 'delete clear'
                _stmts = []
                _stmt_parents = []
                continue
                
        if not are_exclusive(self, node):
            #print 'append', node, node.source_line()
            _stmts.append(node)
            _stmt_parents.append(stmt.parent)
    #print '->', _stmts
    stmts = _stmts
    return stmts


def _decorate(astmodule):
    """add this module functionalities to necessary nodes"""
    for klass in (astmodule.Name, astmodule.Module, astmodule.Class,
                  astmodule.Function, astmodule.Lambda):
        klass.ilookup = ilookup
        klass.lookup = lookup
        klass._filter_stmts = _filter_stmts
    astmodule.Class.scope_lookup = class_scope_lookup
    astmodule.Function.scope_lookup = function_scope_lookup
    astmodule.Lambda.scope_lookup = function_scope_lookup
    astmodule.Module.scope_lookup = scope_lookup
    astmodule.GenExpr.scope_lookup = scope_lookup
    for name in ('Class', 'Function', 'Lambda',
                 'For', 'ListCompFor', 'GenExprFor',
                 'AssName', 'Name', 'Const'):
        globals()[name] = getattr(astmodule, name)
