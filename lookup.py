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

Be careful, lookup is kinda internal and return a tuple (frame, [stmts]), while
ilookup return an iterator on infered values

:version:   $Revision: 1.6 $  
:author:    Sylvain Thenault
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2006 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__revision__ = "$Id: lookup.py,v 1.6 2006-03-06 08:57:53 syt Exp $"
__doctype__ = "restructuredtext en"

import __builtin__

from logilab.astng.utils import are_exclusive
from logilab.astng import MANAGER, _infer_stmts


def lookup(self, name):
    """lookup a variable name

    return the frame and the list of assignments associated to the given name
    according to the scope where it has been found (locals, globals or builtin)

    The lookup is starting from self's frame. If self is not a frame itself and
    the name is found in the inner frame locals, statements will be filtered
    to remove ignorable statements according to self's location
    """
    #assert ID_RGX.match(name), '%r is not a valid identifier' % name
    frame = self.frame()
    offset = 0
    # adjust frame for class'ancestors and function"s arguments
    if isinstance(frame, Class):
        if self in frame.bases:
            #print 'frame swaping'
            frame = frame.parent.frame()
            # line offset to avoid that class A(A) resolve the ancestor to
            # the defined class
            offset = -1
    elif isinstance(frame, (Function, Lambda)):
        if self in frame.defaults:
            frame = frame.parent.frame()
            # line offset to avoid that def func(f=func) resolve the default
            # value to the defined function
            offset = -1
    #print 'lookup', self.__class__, getattr(self, 'name', 'noname'), name
    # resolve name into locals scope
    try:
        stmts = self._filter_stmts(frame.locals[name], frame, offset)
    except KeyError:
        stmts = []
    # lookup name into globals if we were not already at the module level
    if not stmts and frame.parent is not None:
        try:
            frame = frame.root()
            stmts = self._filter_stmts(frame.locals[name], frame, 0)
            #stmts = frame.locals[name]
        except KeyError:
            pass
    # lookup name into builtins
    if not stmts:
        frame, stmts = builtin_lookup(name)
    #print 'return', name, frame.name, [(stmt.__class__.__name__, getattr(stmt, 'name', '???')) for stmt in stmts]
    return frame, stmts

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

def ilookup(self, name, path=None):
    """infered lookup
    
    return an iterator on infered values of the statements returned by
    the lookup method
    """
    frame, stmts = self.lookup(name)
    return _infer_stmts(stmts, name, path, frame)


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
                #print list(ass_type.assigned_stmts())
                #if ass_type.assigned_stmts()
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
    for name in ('Class', 'Function', 'Lambda',
                 'For', 'ListCompFor', 'GenExprFor',
                 'AssName', 'Name', 'Const'):
        globals()[name] = getattr(astmodule, name)
