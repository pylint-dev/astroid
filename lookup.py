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
"""name lookup methods, available on Name and scoped nodes (Module, Class,
Function, Lambda, GenExpr...):

* .lookup(name)
* .ilookup(name)

Be careful, lookup is internal and returns a tuple (scope, [stmts]), while
ilookup returns an iterator on infered values.

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__docformat__ = "restructuredtext en"

import __builtin__

from logilab.astng import MANAGER, NotFoundError
from logilab.astng import _nodes as nodes
from logilab.astng.infutils import are_exclusive, copy_context, _infer_stmts


class LookupMixIn(object):
    """Mixin looking up a name in the right scope
    """

    def lookup(self, name):
        """lookup a variable name

        return the scope node and the list of assignments associated to the given
        name according to the scope where it has been found (locals, globals or
        builtin)

        The lookup is starting from self's scope. If self is not a frame itself and
        the name is found in the inner frame locals, statements will be filtered
        to remove ignorable statements according to self's location
        """
        return self.scope().scope_lookup(self, name)

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
        """filter statements to remove ignorable statements.

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
        mystmt = self.statement()
        # line filtering if we are in the same frame
        #
        # take care node may be missing lineno information (this is the case for
        # nodes inserted for living objects)
        if myframe is frame and mystmt.fromlineno is not None:
            assert mystmt.fromlineno is not None, mystmt
            mylineno = mystmt.fromlineno + offset
        else:
            # disabling lineno filtering
            mylineno = 0
        _stmts = []
        _stmt_parents = []
        for node in stmts:
            stmt = node.statement()
            # line filtering is on and we have reached our location, break
            if mylineno > 0 and stmt.fromlineno > mylineno:
                break
            if isinstance(node, nodes.Class) and self in node.bases:
                break
            assert hasattr(node, 'ass_type'), (node, node.scope(),
                                               node.scope().locals)
            ass_type = node.ass_type()
            if ass_type is mystmt and not isinstance(ass_type, (nodes.Class,
                    nodes.Function, nodes.Import, nodes.From, nodes.Lambda)):
                if not isinstance(ass_type, nodes.Comprehension):
                    break
                if isinstance(self, (nodes.Const, nodes.Name)):
                    _stmts = [self]
                    break
            elif ass_type.statement() is mystmt:
                # original node's statement is the assignment, only keeps
                # current node (gen exp, list comp)
                _stmts = [node]
                break        
            optional_assign = isinstance(ass_type, nodes.LOOP_SCOPES)
            if optional_assign and ass_type.parent_of(self):
                # we are inside a loop, loop var assigment is hidding previous
                # assigment
                _stmts = [node]
                _stmt_parents = [stmt.parent]
                continue
            # XXX comment various branches below!!!
            try:
                pindex = _stmt_parents.index(stmt.parent)
            except ValueError:
                pass
            else:
                # we got a parent index, this means the currently visited node
                # is at the same block level as a previously visited node
                if _stmts[pindex].ass_type().parent_of(ass_type):
                    # both statements are not at the same block level
                    continue
                # if currently visited node is following previously considered
                # assignement and both are not exclusive, we can drop the
                # previous one. For instance in the following code ::
                #
                #   if a:
                #     x = 1
                #   else:
                #     x = 2
                #   print x
                #
                # we can't remove neither x = 1 nor x = 2 when looking for 'x'
                # of 'print x'; while in the following ::
                #
                #   x = 1
                #   x = 2
                #   print x
                #
                # we can remove x = 1 when we see x = 2
                #
                # moreover, on loop assignment types, assignment won't
                # necessarily be done if the loop has no iteration, so we don't
                # want to clear previous assigments if any (hence the test on
                # optional_assign)
                if not (optional_assign or are_exclusive(_stmts[pindex], node)):
                    del _stmt_parents[pindex]
                    del _stmts[pindex]
            if isinstance(node, nodes.AssName):
                if not optional_assign and stmt.parent is mystmt.parent:
                    _stmts = []
                    _stmt_parents = []
            elif isinstance(node, nodes.DelName):
                _stmts = []
                _stmt_parents = []
                continue
            if not are_exclusive(self, node):
                _stmts.append(node)
                _stmt_parents.append(stmt.parent)
        return _stmts


def builtin_lookup(name):
    """lookup a name into the builtin module
    return the list of matching statements and the astng for the builtin
    module
    """
    builtinastng = MANAGER.astng_from_module(__builtin__)
    if name == '__dict__':
        return builtinastng, ()
    try:
        stmts = builtinastng.locals[name]
    except KeyError:
        stmts = ()
    return builtinastng, stmts


class LocalsDictMixIn(object):
    """ this class provides locals handling common to Module, Function
    and Class nodes, including a dict like interface for direct access
    to locals information

    /!\ this class should not be used directly /!\ it's
    only used as a methods and attribute container, and update the
    original class from the compiler.ast module using its dictionary
    (see below the class definition)
    """

    # attributes below are set by the builder module or by raw factories

    # dictionary of locals with name as key and node defining the local as
    # value
    locals = None

    def qname(self):
        """return the 'qualified' name of the node, eg module.name,
        module.class.name ...
        """
        if self.parent is None:
            return self.name
        return '%s.%s' % (self.parent.frame().qname(), self.name)

    def frame(self):
        """return the first parent frame node (i.e. Module, Function or Class)
        """
        return self

    def scope(self):
        """return the first node defining a new scope (i.e. Module,
        Function, Class, Lambda but also GenExpr)
        """
        return self


    def _scope_lookup(self, node, name, offset=0):
        """XXX method for interfacing the scope lookup"""
        try:
            stmts = node._filter_stmts(self.locals[name], self, offset)
        except KeyError:
            stmts = ()
        if stmts:
            return self, stmts
        if self.parent: # i.e. not Module
            # nested scope: if parent scope is a function, that's fine
            # else jump to the module
            pscope = self.parent.scope()
            if not isinstance(pscope, nodes.Function):
                pscope = pscope.root()
            return pscope.scope_lookup(node, name)
        return builtin_lookup(name) # Module



    def set_local(self, name, stmt):
        """define <name> in locals (<stmt> is the node defining the name)
        if the node is a Module node (i.e. has globals), add the name to
        globals

        if the name is already defined, ignore it
        """
        assert self.locals is not None, (self, id(self))
        #assert not stmt in self.locals.get(name, ()), (self, stmt)
        self.locals.setdefault(name, []).append(stmt)

    __setitem__ = set_local

    def _append_node(self, child):
        """append a child, linking it in the tree"""
        self.body.append(child)
        child.parent = self

    def add_local_node(self, child_node, name=None):
        """append a child which should alter locals to the given node"""
        if name != '__class__':
            # add __class__ node as a child will cause infinite recursion later!
            self._append_node(child_node)
        self.set_local(name or child_node.name, child_node)


    def __getitem__(self, item):
        """method from the `dict` interface returning the first node
        associated with the given name in the locals dictionary

        :type item: str
        :param item: the name of the locally defined object
        :raises KeyError: if the name is not defined
        """
        return self.locals[item][0]

    def __iter__(self):
        """method from the `dict` interface returning an iterator on
        `self.keys()`
        """
        return iter(self.keys())

    def keys(self):
        """method from the `dict` interface returning a tuple containing
        locally defined names
        """
        return self.locals.keys()

    def values(self):
        """method from the `dict` interface returning a tuple containing
        locally defined nodes which are instance of `Function` or `Class`
        """
        return [self[key] for key in self.keys()]

    def items(self):
        """method from the `dict` interface returning a list of tuple
        containing each locally defined name with its associated node,
        which is an instance of `Function` or `Class`
        """
        return zip(self.keys(), self.values())

    def has_key(self, name):
        """method from the `dict` interface returning True if the given
        name is defined in the locals dictionary
        """
        return self.locals.has_key(name)

    __contains__ = has_key


