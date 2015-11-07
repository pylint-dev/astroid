# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
"""This module contains some mixins for the different nodes.
"""

import warnings

from astroid import context
from astroid import decorators
from astroid import exceptions
from astroid.interpreter import util as interpreterutil
from astroid.tree import treeabc
from astroid import util


class BlockRangeMixIn(object):
    """override block range """

    @decorators.cachedproperty
    def blockstart_tolineno(self):
        return self.lineno

    def _elsed_block_range(self, lineno, orelse, last=None):
        """handle block line numbers range for try/finally, for, if and while
        statements
        """
        if lineno == self.fromlineno:
            return lineno, lineno
        if orelse:
            if lineno >= orelse[0].fromlineno:
                return lineno, orelse[-1].tolineno
            return lineno, orelse[0].fromlineno - 1
        return lineno, last or self.tolineno


class FilterStmtsMixin(object):
    """Mixin for statement filtering and assignment type"""

    def _get_filtered_stmts(self, _, node, _stmts, mystmt):
        """method used in _filter_stmts to get statemtents and trigger break"""
        if self.statement() is mystmt:
            # original node's statement is the assignment, only keep
            # current node (gen exp, list comp)
            return [node], True
        return _stmts, False

    def assign_type(self):
        return self

    def ass_type(self):
        warnings.warn('%s.ass_type() is deprecated and slated for removal '
                      'in astroid 2.0, use %s.assign_type() instead.'
                      % (type(self).__name__, type(self).__name__),
                      PendingDeprecationWarning, stacklevel=2)
        return self.assign_type()


class AssignTypeMixin(object):

    def assign_type(self):
        return self

    def ass_type(self):
        warnings.warn('%s.ass_type() is deprecated and slated for removal '
                      'in astroid 2.0, use %s.assign_type() instead.'
                      % (type(self).__name__, type(self).__name__),
                      PendingDeprecationWarning, stacklevel=2)
        return self.assign_type()

    def _get_filtered_stmts(self, lookup_node, node, _stmts, mystmt):
        """method used in filter_stmts"""
        if self is mystmt:
            return _stmts, True
        if self.statement() is mystmt:
            # original node's statement is the assignment, only keep
            # current node (gen exp, list comp)
            return [node], True
        return _stmts, False


class ParentAssignTypeMixin(AssignTypeMixin):

    def assign_type(self):
        return self.parent.assign_type()

    def ass_type(self):
        warnings.warn('%s.ass_type() is deprecated and slated for removal '
                      'in astroid 2.0, use %s.assign_type() instead.'
                      % (type(self).__name__, type(self).__name__),
                      PendingDeprecationWarning, stacklevel=2)
        return self.assign_type()


class ImportFromMixin(FilterStmtsMixin):
    """MixIn for From and Import Nodes"""

    def _infer_name(self, frame, name):
        return name

    def do_import_module(self, modname=None):
        """return the ast for a module whose name is <modname> imported by <self>
        """
        # handle special case where we are on a package node importing a module
        # using the same name as the package, which may end in an infinite loop
        # on relative imports
        # XXX: no more needed ?
        mymodule = self.root()
        level = getattr(self, 'level', None) # Import as no level
        if modname is None:
            modname = self.modname
        # XXX we should investigate deeper if we really want to check
        # importing itself: modname and mymodule.name be relative or absolute
        if mymodule.relative_to_absolute_name(modname, level) == mymodule.name:
            # FIXME: we used to raise InferenceError here, but why ?
            return mymodule
        try:
            return mymodule.import_module(modname, level=level,
                                          relative_only=level and level >= 1)
        except exceptions.AstroidBuildingException as ex:
            if isinstance(ex.args[0], SyntaxError):
                util.reraise(exceptions.InferenceError(str(ex)))
            util.reraise(exceptions.InferenceError(modname))
        except SyntaxError as ex:
            util.reraise(exceptions.InferenceError(str(ex)))

    def real_name(self, asname):
        """get name from 'as' name"""
        for name, _asname in self.names:
            if name == '*':
                return asname
            if not _asname:
                name = name.split('.', 1)[0]
                _asname = name
            if asname == _asname:
                return name
        raise exceptions.NotFoundError(asname)


class LookupMixIn(object):
    """Mixin looking up a name in the right scope
    """

    def lookup(self, name):
        """lookup a variable name

        return the scope node and the list of assignments associated to the
        given name according to the scope where it has been found (locals,
        globals or builtin)

        The lookup is starting from self's scope. If self is not a frame itself
        and the name is found in the inner frame locals, statements will be
        filtered to remove ignorable statements according to self's location
        """
        return self.scope().scope_lookup(self, name)

    def ilookup(self, name):
        """inferred lookup

        return an iterator on inferred values of the statements returned by
        the lookup method
        """
        frame, stmts = self.lookup(name)
        return interpreterutil.infer_stmts(stmts, context.InferenceContext(), frame)

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
            # If the frame of this node is the same as the statement
            # of this node, then the node is part of a class or
            # a function definition and the frame of this node should be the
            # the upper frame, not the frame of the definition.
            # For more information why this is important,
            # see Pylint issue #295.
            # For example, for 'b', the statement is the same
            # as the frame / scope:
            #
            # def test(b=1):
            #     ...

            if self.statement() is myframe and myframe.parent:
                myframe = myframe.parent.frame()
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
            assert hasattr(node, 'assign_type'), (node, node.scope(),
                                                  node.scope().locals)
            assign_type = node.assign_type()

            if node.has_base(self):
                break

            _stmts, done = assign_type._get_filtered_stmts(self, node, _stmts, mystmt)
            if done:
                break

            optional_assign = assign_type.optional_assign
            if optional_assign and assign_type.parent_of(self):
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
                if _stmts[pindex].assign_type().parent_of(assign_type):
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
                if not (optional_assign or interpreterutil.are_exclusive(_stmts[pindex], node)):
                    del _stmt_parents[pindex]
                    del _stmts[pindex]
            if isinstance(node, treeabc.AssignName):
                if not optional_assign and stmt.parent is mystmt.parent:
                    _stmts = []
                    _stmt_parents = []
            elif isinstance(node, treeabc.DelName):
                _stmts = []
                _stmt_parents = []
                continue
            if not interpreterutil.are_exclusive(self, node):
                _stmts.append(node)
                _stmt_parents.append(stmt.parent)
        return _stmts
