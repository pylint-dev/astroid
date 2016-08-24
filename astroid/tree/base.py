# Copyright (c) 2015-2016 Cara Vinson <ceridwenv@gmail.com>
# Copyright (c) 2015-2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


import abc
import pprint

import six

from astroid import as_string
from astroid import context
from astroid import decorators
from astroid import exceptions
from astroid.interpreter import scope
from astroid.interpreter import util as interpreterutil
from astroid.tree import treeabc
from astroid import util

inference = util.lazy_import('inference')


@util.register_implementation(treeabc.NodeNG)
class NodeNG(object):
    """Base Class for all Astroid node classes.

    It represents a node of the new abstract syntax tree.
    """
    is_statement = False
    optional_assign = False # True for For (and for Comprehension if py <3.0)
    is_function = False # True for FunctionDef nodes
    # attributes below are set by the builder module or by raw factories
    lineno = None
    col_offset = None
    # parent node in the tree
    parent = None
    # attributes containing child node(s) redefined in most concrete classes:
    _astroid_fields = ()
    # attributes containing non-nodes:
    _other_fields = ()
    # attributes containing AST-dependent fields:
    _other_other_fields = ()
    # instance specific inference function infer(node, context)
    _explicit_inference = None

    def __init__(self, lineno=None, col_offset=None, parent=None):
        self.lineno = lineno
        self.col_offset = col_offset
        self.parent = parent

    def infer(self, context=None, **kwargs):
        """main interface to the interface system, return a generator on inferred
        values.

        If the instance has some explicit inference function set, it will be
        called instead of the default interface.
        """
        if self._explicit_inference is not None:
            # explicit_inference is not bound, give it self explicitly
            try:
                # pylint: disable=not-callable
                return self._explicit_inference(self, context, **kwargs)
            except exceptions.UseInferenceDefault:
                pass

        if not context:
            return inference.infer(self, context, **kwargs)

        key = (self, context.lookupname,
               context.callcontext, context.boundnode)
        if key in context.inferred:
            return iter(context.inferred[key])

        return context.cache_generator(key, inference.infer(self, context, **kwargs))

    def _repr_name(self):
        """return self.name or self.attrname or '' for nice representation"""
        return getattr(self, 'name', getattr(self, 'attrname', ''))

    def __str__(self):
        rname = self._repr_name()
        cname = type(self).__name__
        if rname:
            string = '%(cname)s.%(rname)s(%(fields)s)'
            alignment = len(cname) + len(rname) + 2
        else:
            string = '%(cname)s(%(fields)s)'
            alignment = len(cname) + 1
        result = []
        for field in self._other_fields + self._astroid_fields:
            value = getattr(self, field)
            width = 80 - len(field) - alignment
            lines = pprint.pformat(value, indent=2,
                                   width=width).splitlines(True)

            inner = [lines[0]]
            for line in lines[1:]:
                inner.append(' ' * alignment + line)
            result.append('%s=%s' % (field, ''.join(inner)))

        return string % {'cname': cname,
                         'rname': rname,
                         'fields': (',\n' + ' ' * alignment).join(result)}

    def __repr__(self):
        rname = self._repr_name()
        if rname:
            string = '<%(cname)s.%(rname)s l.%(lineno)s at 0x%(id)x>'
        else:
            string = '<%(cname)s l.%(lineno)s at 0x%(id)x>'
        return string % {'cname': type(self).__name__,
                         'rname': rname,
                         'lineno': self.fromlineno,
                         'id': id(self)}

    def accept(self, visitor):
        func = getattr(visitor, "visit_" + self.__class__.__name__.lower())
        return func(self)

    def get_children(self):
        for field in self._astroid_fields:
            attr = getattr(self, field)
            if attr is None:
                continue
            if isinstance(attr, (list, tuple)):
                for elt in attr:
                    yield elt
            else:
                yield attr

    def last_child(self):
        """an optimized version of list(get_children())[-1]"""
        for field in self._astroid_fields[::-1]:
            attr = getattr(self, field)
            if not attr: # None or empty listy / tuple
                continue
            if isinstance(attr, (list, tuple)):
                return attr[-1]
            else:
                return attr
        return None

    def parent_of(self, node):
        """return true if i'm a parent of the given node"""
        parent = node.parent
        while parent is not None:
            if self is parent:
                return True
            parent = parent.parent
        return False

    def statement(self):
        """return the first parent node marked as statement node"""
        if self.is_statement:
            return self
        return self.parent.statement()

    def frame(self):
        """return the first parent frame node (i.e. Module, FunctionDef or
        ClassDef)

        """
        return self.parent.frame()

    def scope(self):
        """Get the first node defining a new scope

        Scopes are introduced in Python by Module, FunctionDef, ClassDef,
        Lambda, GenExpr and on Python 3, by comprehensions.
        """
        return scope.node_scope(self)

    def root(self):
        """return the root node of the tree, (i.e. a Module)"""
        if self.parent:
            return self.parent.root()
        return self

    def child_sequence(self, child):
        """search for the right sequence where the child lies in"""
        for field in self._astroid_fields:
            node_or_sequence = getattr(self, field)
            if node_or_sequence is child:
                return [node_or_sequence]
            # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
            if (isinstance(node_or_sequence, (tuple, list))
                    and child in node_or_sequence):
                return node_or_sequence

        msg = 'Could not find %s in %s\'s children'
        raise exceptions.AstroidError(msg % (repr(child), repr(self)))

    def locate_child(self, child):
        """return a 2-uple (child attribute name, sequence or node)"""
        for field in self._astroid_fields:
            node_or_sequence = getattr(self, field)
            # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
            if child is node_or_sequence:
                return field, child
            if isinstance(node_or_sequence, (tuple, list)) and child in node_or_sequence:
                return field, node_or_sequence
        msg = 'Could not find %s in %s\'s children'
        raise exceptions.AstroidError(msg % (repr(child), repr(self)))
    # FIXME : should we merge child_sequence and locate_child ? locate_child
    # is only used in are_exclusive, child_sequence one time in pylint.

    def next_sibling(self):
        """return the next sibling statement"""
        return self.parent.next_sibling()

    def previous_sibling(self):
        """return the previous sibling statement"""
        return self.parent.previous_sibling()

    # these are lazy because they're relatively expensive to compute for every
    # single node, and they rarely get looked at

    @decorators.cachedproperty
    def fromlineno(self):
        return self.lineno

    @decorators.cachedproperty
    def tolineno(self):
        if not self._astroid_fields:
            # can't have children
            lastchild = None
        else:
            lastchild = self.last_child()
        if lastchild is None:
            return self.fromlineno
        else:
            return lastchild.tolineno

    def block_range(self, lineno):
        """handle block line numbers range for non block opening statements
        """
        return lineno, self.tolineno

    def set_local(self, name, stmt):
        """delegate to a scoped parent handling a locals dictionary"""
        self.parent.set_local(name, stmt)

    def nodes_of_class(self, klass, skip_klass=None):
        """return an iterator on nodes which are instance of the given class(es)

        klass may be a class object or a tuple of class objects
        """
        if isinstance(self, klass):
            yield self
        for child_node in self.get_children():
            if skip_klass is not None and isinstance(child_node, skip_klass):
                continue
            for matching in child_node.nodes_of_class(klass, skip_klass):
                yield matching

    def _infer_name(self, frame, name):
        # overridden for ImportFrom, Import, Global, TryExcept and Arguments
        return None

    def _infer(self, context=None):
        """we don't know how to resolve a statement by default"""
        # this method is overridden by most concrete classes
        raise exceptions.InferenceError(self.__class__.__name__)

    def inferred(self):
        '''return list of inferred values for a more simple inference usage'''
        return list(self.infer())

    def instantiate_class(self):
        """instanciate a node if it is a ClassDef node, else return self"""
        return self

    def has_base(self, node):
        return False

    def callable(self):
        return False

    def eq(self, value):
        return False

    def as_string(self):
        return as_string.to_code(self)

    def repr_tree(self, ids=False, include_linenos=False,
                  ast_state=False, indent='   ', max_depth=0, max_width=80):
        """Returns a string representation of the AST from this node.

        Args:
            ids (bool): If true, includes the ids with the node type names.
            include_linenos (bool): If true, includes the line numbers and
                column offsets.
            ast_state (bool): If true, includes information derived from
                the whole AST like local and global variables.
            indent (str): A string to use to indent the output string.
            max_depth (int): If set to a positive integer, won't return
                nodes deeper than max_depth in the string.
            max_width (int): Only positive integer values are valid, the
                default is 80.  Attempts to format the output string to stay
                within max_width characters, but can exceed it under some
                circumstances.
        """
        @util.singledispatch
        def _repr_tree(node, result, done, cur_indent='', depth=1):
            """Outputs a representation of a non-tuple/list, non-node that's
            contained within an AST, including strings.
            """
            lines = pprint.pformat(node,
                                   width=max(max_width - len(cur_indent),
                                             1)).splitlines(True)
            result.append(lines[0])
            result.extend([cur_indent + line for line in lines[1:]])
            return len(lines) != 1

        # pylint: disable=unused-variable; doesn't understand singledispatch
        @_repr_tree.register(tuple)
        @_repr_tree.register(list)
        def _repr_seq(node, result, done, cur_indent='', depth=1):
            """Outputs a representation of a sequence that's contained within an AST."""
            cur_indent += indent
            result.append('[')
            if len(node) == 0:
                broken = False
            elif len(node) == 1:
                broken = _repr_tree(node[0], result, done, cur_indent, depth)
            elif len(node) == 2:
                broken = _repr_tree(node[0], result, done, cur_indent, depth)
                if not broken:
                    result.append(', ')
                else:
                    result.append(',\n')
                    result.append(cur_indent)
                broken = (_repr_tree(node[1], result, done, cur_indent, depth)
                          or broken)
            else:
                result.append('\n')
                result.append(cur_indent)
                for child in node[:-1]:
                    _repr_tree(child, result, done, cur_indent, depth)
                    result.append(',\n')
                    result.append(cur_indent)
                _repr_tree(node[-1], result, done, cur_indent, depth)
                broken = True
            result.append(']')
            return broken

        # pylint: disable=unused-variable; doesn't understand singledispatch
        @_repr_tree.register(NodeNG)
        def _repr_node(node, result, done, cur_indent='', depth=1):
            """Outputs a strings representation of an astroid node."""
            if node in done:
                result.append(indent + '<Recursion on %s with id=%s' %
                              (type(node).__name__, id(node)))
                return False
            else:
                done.add(node)
            if max_depth and depth > max_depth:
                result.append('...')
                return False
            depth += 1
            cur_indent += indent
            if ids:
                result.append('%s<0x%x>(\n' % (type(node).__name__, id(node)))
            else:
                result.append('%s(' % type(node).__name__)
            fields = []
            if include_linenos:
                fields.extend(('lineno', 'col_offset'))
            fields.extend(node._other_fields)
            fields.extend(node._astroid_fields)
            if ast_state:
                fields.extend(node._other_other_fields)
            if len(fields) == 0:
                broken = False
            elif len(fields) == 1:
                result.append('%s=' % fields[0])
                broken = _repr_tree(getattr(node, fields[0]), result, done,
                                    cur_indent, depth)
            else:
                result.append('\n')
                result.append(cur_indent)
                for field in fields[:-1]:
                    result.append('%s=' % field)
                    _repr_tree(getattr(node, field), result, done, cur_indent,
                               depth)
                    result.append(',\n')
                    result.append(cur_indent)
                result.append('%s=' % fields[-1])
                _repr_tree(getattr(node, fields[-1]), result, done, cur_indent,
                           depth)
                broken = True
            result.append(')')
            return broken

        result = []
        _repr_tree(self, result, set())
        return ''.join(result)

    def print_tree(self, *args, **kws):
        """Shortcut method to print the result of repr_tree()."""
        print(self.repr_tree(*args, **kws))

    def bool_value(self):
        """Determine the bool value of this node

        The boolean value of a node can have three
        possible values:

            * False. For instance, empty data structures,
              False, empty strings, instances which return
              explicitly False from the __nonzero__ / __bool__
              method.
            * True. Most of constructs are True by default:
              classes, functions, modules etc
            * Uninferable: the inference engine is uncertain of the
              node's value.
        """
        return util.Uninferable


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


class AssignTypeMixin(object):

    def assign_type(self):
        return self

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

        mystmt = self.statement()
        # line filtering if we are in the same frame
        #
        # take care node may be missing lineno information (this is the case for
        # nodes inserted for living objects)
        if myframe is frame and mystmt.fromlineno is not None:
            mylineno = mystmt.fromlineno + offset
        else:
            # disabling lineno filtering
            mylineno = 0
        _stmts = []
        _stmt_parents = []
        for node in stmts:
            stmt = node.statement()
            # line filtering is on and we have reached our location, break
            if mylineno > 0 and stmt.fromlineno and stmt.fromlineno > mylineno:
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
            if isinstance(node, (treeabc.Parameter, treeabc.AssignName)):
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


@six.add_metaclass(abc.ABCMeta)
class BaseContainer(ParentAssignTypeMixin, NodeNG):
    """Base class for Set, FrozenSet, Tuple and List."""

    _astroid_fields = ('elts',)

    def __init__(self, lineno=None, col_offset=None, parent=None):
        self.elts = []
        super(BaseContainer, self).__init__(lineno, col_offset, parent)

    def postinit(self, elts):
        self.elts = elts

    def itered(self):
        return self.elts

    def bool_value(self):
        return bool(self.elts)

    @abc.abstractmethod
    def pytype(self):
        pass
