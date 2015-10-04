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
"""This module contains base classes and functions for the nodes and some
inference utils.
"""

from __future__ import print_function

import collections
import functools
import itertools
import pprint
import sys
import warnings

try:
    from functools import singledispatch as _singledispatch
except ImportError:
    from singledispatch import singledispatch as _singledispatch

import wrapt

from astroid import as_string
from astroid import context as contextmod
from astroid import decorators as decoratorsmod
from astroid import exceptions
from astroid import util


if sys.version_info >= (3, 0):
    BUILTINS = 'builtins'
    BOOL_SPECIAL_METHOD = '__bool__'
else:
    BUILTINS = '__builtin__'
    BOOL_SPECIAL_METHOD = '__nonzero__'
PROPERTIES = {BUILTINS + '.property', 'abc.abstractproperty'}
# List of possible property names. We use this list in order
# to see if a method is a property or not. This should be
# pretty reliable and fast, the alternative being to check each
# decorator to see if its a real property-like descriptor, which
# can be too complicated.
# Also, these aren't qualified, because each project can
# define them, we shouldn't expect to know every possible
# property-like decorator!
# TODO(cpopa): just implement descriptors already.
POSSIBLE_PROPERTIES = {"cached_property", "cachedproperty",
                       "lazyproperty", "lazy_property", "reify",
                       "lazyattribute", "lazy_attribute",
                       "LazyProperty"}


def _is_property(meth):
    if PROPERTIES.intersection(meth.decoratornames()):
        return True
    stripped = {name.split(".")[-1] for name in meth.decoratornames()
                if name is not util.YES}
    return any(name in stripped for name in POSSIBLE_PROPERTIES)


class Proxy(object):
    """a simple proxy object"""

    _proxied = None # proxied object may be set by class or by instance

    def __init__(self, proxied=None):
        if proxied is not None:
            self._proxied = proxied

    def __getattr__(self, name):
        if name == '_proxied':
            return getattr(self.__class__, '_proxied')
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self._proxied, name)

    def infer(self, context=None):
        yield self


def _infer_stmts(stmts, context, frame=None):
    """Return an iterator on statements inferred by each statement in *stmts*."""
    stmt = None
    inferred = False
    if context is not None:
        name = context.lookupname
        context = context.clone()
    else:
        name = None
        context = contextmod.InferenceContext()

    for stmt in stmts:
        if stmt is util.YES:
            yield stmt
            inferred = True
            continue
        context.lookupname = stmt._infer_name(frame, name)
        try:
            for inferred in stmt.infer(context=context):
                yield inferred
                inferred = True
        except exceptions.UnresolvableName:
            continue
        except exceptions.InferenceError:
            yield util.YES
            inferred = True
    if not inferred:
        raise exceptions.InferenceError(str(stmt))


def _infer_method_result_truth(instance, method_name, context):
    # Get the method from the instance and try to infer
    # its return's truth value.
    meth = next(instance.igetattr(method_name, context=context), None)
    if meth and hasattr(meth, 'infer_call_result'):
        for value in meth.infer_call_result(instance, context=context):
            if value is util.YES:
                return value

            inferred = next(value.infer(context=context))
            return inferred.bool_value()
    return util.YES


class Instance(Proxy):
    """A special node representing a class instance."""

    def getattr(self, name, context=None, lookupclass=True):
        try:
            values = self._proxied.instance_attr(name, context)
        except exceptions.NotFoundError:
            if name == '__class__':
                return [self._proxied]
            if lookupclass:
                # Class attributes not available through the instance
                # unless they are explicitly defined.
                if name in ('__name__', '__bases__', '__mro__', '__subclasses__'):
                    return self._proxied.local_attr(name)
                return self._proxied.getattr(name, context,
                                             class_context=False)
            util.reraise(exceptions.NotFoundError(name))
        # since we've no context information, return matching class members as
        # well
        if lookupclass:
            try:
                return values + self._proxied.getattr(name, context,
                                                      class_context=False)
            except exceptions.NotFoundError:
                pass
        return values

    def igetattr(self, name, context=None):
        """inferred getattr"""
        if not context:
            context = contextmod.InferenceContext()
        try:
            # avoid recursively inferring the same attr on the same class
            if context.push((self._proxied, name)):
                return

            # XXX frame should be self._proxied, or not ?
            get_attr = self.getattr(name, context, lookupclass=False)
            for stmt in _infer_stmts(self._wrap_attr(get_attr, context),
                                     context, frame=self):
                yield stmt
        except exceptions.NotFoundError:
            try:
                # fallback to class'igetattr since it has some logic to handle
                # descriptors
                for stmt in self._wrap_attr(self._proxied.igetattr(name, context),
                                            context):
                    yield stmt
            except exceptions.NotFoundError:
                util.reraise(exceptions.InferenceError(name))

    def _wrap_attr(self, attrs, context=None):
        """wrap bound methods of attrs in a InstanceMethod proxies"""
        for attr in attrs:
            if isinstance(attr, UnboundMethod):
                if _is_property(attr):
                    for inferred in attr.infer_call_result(self, context):
                        yield inferred
                else:
                    yield BoundMethod(attr, self)
            elif hasattr(attr, 'name') and attr.name == '<lambda>':
                # This is a lambda function defined at class level,
                # since its scope is the underlying _proxied class.
                # Unfortunately, we can't do an isinstance check here,
                # because of the circular dependency between astroid.bases
                # and astroid.scoped_nodes.
                if attr.statement().scope() == self._proxied:
                    if attr.args.args and attr.args.args[0].name == 'self':
                        yield BoundMethod(attr, self)
                        continue
                yield attr
            else:
                yield attr

    def infer_call_result(self, caller, context=None):
        """infer what a class instance is returning when called"""
        inferred = False
        for node in self._proxied.igetattr('__call__', context):
            if node is util.YES:
                continue
            for res in node.infer_call_result(caller, context):
                inferred = True
                yield res
        if not inferred:
            raise exceptions.InferenceError()

    def __repr__(self):
        return '<Instance of %s.%s at 0x%s>' % (self._proxied.root().name,
                                                self._proxied.name,
                                                id(self))
    def __str__(self):
        return 'Instance of %s.%s' % (self._proxied.root().name,
                                      self._proxied.name)

    def callable(self):
        try:
            self._proxied.getattr('__call__', class_context=False)
            return True
        except exceptions.NotFoundError:
            return False

    def pytype(self):
        return self._proxied.qname()

    def display_type(self):
        return 'Instance of'

    def bool_value(self):
        """Infer the truth value for an Instance

        The truth value of an instance is determined by these conditions:

           * if it implements __bool__ on Python 3 or __nonzero__
             on Python 2, then its bool value will be determined by
             calling this special method and checking its result.
           * when this method is not defined, __len__() is called, if it
             is defined, and the object is considered true if its result is
             nonzero. If a class defines neither __len__() nor __bool__(),
             all its instances are considered true.
        """
        context = contextmod.InferenceContext()
        try:
            result = _infer_method_result_truth(self, BOOL_SPECIAL_METHOD, context)
        except (exceptions.InferenceError, exceptions.NotFoundError):
            # Fallback to __len__.
            try:
                result = _infer_method_result_truth(self, '__len__', context)
            except (exceptions.NotFoundError, exceptions.InferenceError):
                return True
        return result

    # TODO(cpopa): this is set in inference.py
    # The circular dependency hell goes deeper and deeper.
    # pylint: disable=unused-argument
    def getitem(self, index, context=None):
        pass



class UnboundMethod(Proxy):
    """a special node representing a method not bound to an instance"""
    def __repr__(self):
        frame = self._proxied.parent.frame()
        return '<%s %s of %s at 0x%s' % (self.__class__.__name__,
                                         self._proxied.name,
                                         frame.qname(), id(self))

    def is_bound(self):
        return False

    def getattr(self, name, context=None):
        if name == 'im_func':
            return [self._proxied]
        return self._proxied.getattr(name, context)

    def igetattr(self, name, context=None):
        if name == 'im_func':
            return iter((self._proxied,))
        return self._proxied.igetattr(name, context)

    def infer_call_result(self, caller, context):
        # If we're unbound method __new__ of builtin object, the result is an
        # instance of the class given as first argument.
        if (self._proxied.name == '__new__' and
                self._proxied.parent.frame().qname() == '%s.object' % BUILTINS):
            infer = caller.args[0].infer() if caller.args else []
            return ((x is util.YES and x or Instance(x)) for x in infer)
        return self._proxied.infer_call_result(caller, context)

    def bool_value(self):
        return True


class BoundMethod(UnboundMethod):
    """a special node representing a method bound to an instance"""
    def __init__(self, proxy, bound):
        UnboundMethod.__init__(self, proxy)
        self.bound = bound

    def is_bound(self):
        return True

    def _infer_type_new_call(self, caller, context):
        """Try to infer what type.__new__(mcs, name, bases, attrs) returns.

        In order for such call to be valid, the metaclass needs to be
        a subtype of ``type``, the name needs to be a string, the bases
        needs to be a tuple of classes and the attributes a dictionary
        of strings to values.
        """
        from astroid import node_classes
        # Verify the metaclass
        mcs = next(caller.args[0].infer(context=context))
        if mcs.__class__.__name__ != 'ClassDef':
            # Not a valid first argument.
            return
        if not mcs.is_subtype_of("%s.type" % BUILTINS):
            # Not a valid metaclass.
            return

        # Verify the name
        name = next(caller.args[1].infer(context=context))
        if name.__class__.__name__ != 'Const':
            # Not a valid name, needs to be a const.
            return
        if not isinstance(name.value, str):
            # Needs to be a string.
            return

        # Verify the bases
        bases = next(caller.args[2].infer(context=context))
        if bases.__class__.__name__ != 'Tuple':
            # Needs to be a tuple.
            return
        inferred_bases = [next(elt.infer(context=context))
                          for elt in bases.elts]
        if any(base.__class__.__name__ != 'ClassDef'
               for base in inferred_bases):
            # All the bases needs to be Classes
            return

        # Verify the attributes.
        attrs = next(caller.args[3].infer(context=context))
        if attrs.__class__.__name__ != 'Dict':
            # Needs to be a dictionary.
            return
        cls_locals = collections.defaultdict(list)
        for key, value in attrs.items:
            key = next(key.infer(context=context))
            value = next(value.infer(context=context))
            if key.__class__.__name__ != 'Const':
                # Something invalid as an attribute.
                return
            if not isinstance(key.value, str):
                # Not a proper attribute.
                return
            cls_locals[key.value].append(value)

        # Build the class from now.
        cls = mcs.__class__(name=name.value, lineno=caller.lineno,
                            col_offset=caller.col_offset,
                            parent=caller)
        empty = node_classes.Pass()
        cls.postinit(bases=bases.elts, body=[empty], decorators=[],
                     newstyle=True, metaclass=mcs)
        cls.locals = cls_locals
        return cls

    def infer_call_result(self, caller, context):
        context = context.clone()
        context.boundnode = self.bound

        if (self.bound.__class__.__name__ == 'ClassDef'
                and self.bound.name == 'type'
                and self.name == '__new__'
                and len(caller.args) == 4
                # TODO(cpopa): this check shouldn't be needed.
                and self._proxied.parent.frame().qname() == '%s.object' % BUILTINS):

            # Check if we have an ``type.__new__(mcs, name, bases, attrs)`` call.
            new_cls = self._infer_type_new_call(caller, context)
            if new_cls:
                return iter((new_cls, ))

        return super(BoundMethod, self).infer_call_result(caller, context)

    def bool_value(self):
        return True


class Generator(Instance):
    """a special node representing a generator.

    Proxied class is set once for all in raw_building.
    """
    def callable(self):
        return False

    def pytype(self):
        return '%s.generator' % BUILTINS

    def display_type(self):
        return 'Generator'

    def bool_value(self):
        return True

    def __repr__(self):
        return '<Generator(%s) l.%s at 0x%s>' % (self._proxied.name, self.lineno, id(self))

    def __str__(self):
        return 'Generator(%s)' % (self._proxied.name)


# decorators ##################################################################

def path_wrapper(func):
    """return the given infer function wrapped to handle the path"""
    # TODO: switch this to wrapt after the monkey-patching is fixed (ceridwen)
    @functools.wraps(func)
    def wrapped(node, context=None, _func=func, **kwargs):
        """wrapper function handling context"""
        if context is None:
            context = contextmod.InferenceContext()
        if context.push(node):
            return

        yielded = set()
        for res in _func(node, context, **kwargs):
            # unproxy only true instance, not const, tuple, dict...
            if res.__class__ is Instance:
                ares = res._proxied
            else:
                ares = res
            if ares not in yielded:
                yield res
                yielded.add(ares)
    return wrapped

@wrapt.decorator
def yes_if_nothing_inferred(func, instance, args, kwargs):
    inferred = False
    for node in func(*args, **kwargs):
        inferred = True
        yield node
    if not inferred:
        yield util.YES

@wrapt.decorator
def raise_if_nothing_inferred(func, instance, args, kwargs):
    inferred = False
    for node in func(*args, **kwargs):
        inferred = True
        yield node
    if not inferred:
        raise exceptions.InferenceError()


# Node  ######################################################################

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

    # def __init__(self, lineno=None, col_offset=None, parent=None):
    #     self.lineno = lineno
    #     self.col_offset = col_offset
    #     self.parent = parent

    def __init__(self, **kws):
        self.lineno = kws.get('lineno', None)
        self.col_offset = kws.get('col_offset', None)
        for field in itertools.chain(self._astroid_fields, self._other_fields):
            try:
                setattr(self, field, kws[field])
            except KeyError:
                pass

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
            return self._infer(context, **kwargs)

        key = (self, context.lookupname,
               context.callcontext, context.boundnode)
        if key in context.inferred:
            return iter(context.inferred[key])

        return context.cache_generator(key, self._infer(context, **kwargs))

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

    # TODO: this is for the alternate zipper, where only nodes can be the focus
    # def children(self):
    #     return tuple(getattr(self, field) for field in self._astroid_fields)

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

    # def last_child(self):
    #     """an optimized version of list(get_children())[-1]"""
    #     for field in self._astroid_fields[::-1]:
    #         attr = getattr(self, field)
    #         if not attr: # None or empty listy / tuple
    #             continue
    #         if isinstance(attr, (list, tuple)):
    #             return attr[-1]
    #         else:
    #             return attr
    #     return None

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
        """return the first node defining a new scope (i.e. Module,
        FunctionDef, ClassDef, Lambda but also GenExpr)

        """
        return self.parent.scope()

    # def root(self):
    #     """return the root node of the tree, (i.e. a Module)"""
    #     if self.parent:
    #         return self.parent.root()
    #     return self

    # def child_sequence(self, child):
    #     """search for the right sequence where the child lies in"""
    #     for field in self._astroid_fields:
    #         node_or_sequence = getattr(self, field)
    #         if node_or_sequence is child:
    #             return [node_or_sequence]
    #         # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
    #         if (isinstance(node_or_sequence, (tuple, list))
    #                 and child in node_or_sequence):
    #             return node_or_sequence

    #     msg = 'Could not find %s in %s\'s children'
    #     raise exceptions.AstroidError(msg % (repr(child), repr(self)))

    # def locate_child(self, child):
    #     """return a 2-uple (child attribute name, sequence or node)"""
    #     for field in self._astroid_fields:
    #         node_or_sequence = getattr(self, field)
    #         # /!\ compiler.ast Nodes have an __iter__ walking over child nodes
    #         if child is node_or_sequence:
    #             return field, child
    #         if isinstance(node_or_sequence, (tuple, list)) and child in node_or_sequence:
    #             return field, node_or_sequence
    #     msg = 'Could not find %s in %s\'s children'
    #     raise exceptions.AstroidError(msg % (repr(child), repr(self)))
    # # FIXME : should we merge child_sequence and locate_child ? locate_child
    # # is only used in are_exclusive, child_sequence one time in pylint.

    # def next_sibling(self):
    #     """return the next sibling statement"""
    #     return self.parent.next_sibling()

    # def previous_sibling(self):
    #     """return the previous sibling statement"""
    #     return self.parent.previous_sibling()

    # def nearest(self, nodes):
    #     """return the node which is the nearest before this one in the
    #     given list of nodes
    #     """
    #     myroot = self.root()
    #     mylineno = self.fromlineno
    #     nearest = None, 0
    #     for node in nodes:
    #         assert node.root() is myroot, \
    #                'nodes %s and %s are not from the same AST' % (self, node)
    #         lineno = node.fromlineno
    #         if node.fromlineno > mylineno:
    #             break
    #         if lineno > nearest[1]:
    #             nearest = node, lineno
    #     # FIXME: raise an exception if nearest is None ?
    #     return nearest[0]

    # these are lazy because they're relatively expensive to compute for every
    # single node, and they rarely get looked at

    @decoratorsmod.cachedproperty
    def fromlineno(self):
        if self.lineno is None:
            return self._fixed_source_line()
        else:
            return self.lineno

    @decoratorsmod.cachedproperty
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

        # TODO / FIXME:
        assert self.fromlineno is not None, self
        assert self.tolineno is not None, self

    def _fixed_source_line(self):
        """return the line number where the given node appears

        we need this method since not all nodes have the lineno attribute
        correctly set...
        """
        line = self.lineno
        _node = self.down()
        try:
            while line is None:
                _node = _node.right()
                line = _node.lineno
        except AttributeError:
            _node = self.parent
            while _node and line is None:
                line = _node.lineno
                _node = _node.parent
        return line

    def block_range(self, lineno):
        """handle block line numbers range for non block opening statements
        """
        return lineno, self.tolineno

    def set_local(self, name, stmt):
        """delegate to a scoped parent handling a locals dictionary"""
        self.parent.set_local(name, stmt)

    # def nodes_of_class(self, klass, skip_klass=None):
    #     """return an iterator on nodes which are instance of the given class(es)

    #     klass may be a class object or a tuple of class objects
    #     """
    #     if isinstance(self, klass):
    #         yield self
    #     for child_node in self.get_children():
    #         if skip_klass is not None and isinstance(child_node, skip_klass):
    #             continue
    #         for matching in child_node.nodes_of_class(klass, skip_klass):
    #             yield matching

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

    def infered(self):
        warnings.warn('%s.infered() is deprecated and slated for removal '
                      'in astroid 2.0, use %s.inferred() instead.'
                      % (type(self).__name__, type(self).__name__),
                      PendingDeprecationWarning, stacklevel=2)
        return self.inferred()

    def instanciate_class(self):
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

        :param ids: If true, includes the ids with the node type names.

        :param include_linenos: If true, includes the line numbers and
            column offsets.

        :param ast_state: If true, includes information derived from
        the whole AST like local and global variables.

        :param indent: A string to use to indent the output string.

        :param max_depth: If set to a positive integer, won't return
        nodes deeper than max_depth in the string.

        :param max_width: Only positive integer values are valid, the
        default is 80.  Attempts to format the output string to stay
        within max_width characters, but can exceed it under some
        circumstances.
        """
        @_singledispatch
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
            * YES: the inference engine is uncertain of the
              node's value.
        """
        return util.YES


class Statement(NodeNG):
    """Statement node adding a few attributes"""
    is_statement = True

    # def next_sibling(self):
    #     """return the next sibling statement"""
    #     stmts = self.parent.child_sequence(self)
    #     index = stmts.index(self)
    #     try:
    #         return stmts[index +1]
    #     except IndexError:
    #         pass

    # def previous_sibling(self):
    #     """return the previous sibling statement"""
    #     stmts = self.parent.child_sequence(self)
    #     index = stmts.index(self)
    #     if index >= 1:
    #         return stmts[index -1]
