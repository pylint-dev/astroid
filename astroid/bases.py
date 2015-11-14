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
import sys
import types

from astroid import context as contextmod
from astroid import decorators
from astroid import exceptions
from astroid import util

node_classes = util.lazy_import('node_classes')
scoped_nodes = util.lazy_import('scoped_nodes')
manager = util.lazy_import('manager')

MANAGER = manager.AstroidManager()


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
                if name is not util.Uninferable}
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
        if name == 'special_attributes' and hasattr(self, 'special_attributes'):
            return self.special_attributes
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
        if stmt is util.Uninferable:
            yield stmt
            inferred = True
            continue
        context.lookupname = stmt._infer_name(frame, name)
        try:
            for inferred in stmt.infer(context=context):
                yield inferred
                inferred = True
        except exceptions.NameInferenceError:
            continue
        except exceptions.InferenceError:
            yield util.Uninferable
            inferred = True
    if not inferred:
        raise exceptions.InferenceError(
            'Inference failed for all members of {stmts!r}.',
            stmts=stmts, frame=frame, context=context)


def _infer_method_result_truth(instance, method_name, context):
    # Get the method from the instance and try to infer
    # its return's truth value.
    meth = next(instance.igetattr(method_name, context=context), None)
    if meth and hasattr(meth, 'infer_call_result'):
        if not meth.callable():
            return util.Uninferable
        for value in meth.infer_call_result(instance, context=context):
            if value is util.Uninferable:
                return value

            inferred = next(value.infer(context=context))
            return inferred.bool_value()
    return util.Uninferable


class Instance(Proxy):
    """A special node representing a class instance."""
    special_attributes = frozenset(('__dict__', '__class__'))

    def getattr(self, name, context=None, lookupclass=True):
        try:
            values = self._proxied.instance_attr(name, context)
        except exceptions.AttributeInferenceError:
            if name == '__class__':
                return [self._proxied]
            if lookupclass:
                # Class attributes not available through the instance
                # unless they are explicitly defined.
                if name in ('__name__', '__bases__', '__mro__', '__subclasses__'):
                    return self._proxied.local_attr(name)
                return self._proxied.getattr(name, context,
                                             class_context=False)
            util.reraise(exceptions.AttributeInferenceError(target=self,
                                                            attribute=name,
                                                            context=context))
        # since we've no context information, return matching class members as
        # well
        if lookupclass:
            try:
                return values + self._proxied.getattr(name, context,
                                                      class_context=False)
            except exceptions.AttributeInferenceError:
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
        except exceptions.AttributeInferenceError:
            try:
                # fallback to class.igetattr since it has some logic to handle
                # descriptors
                for stmt in self._wrap_attr(self._proxied.igetattr(name, context),
                                            context):
                    yield stmt
            except exceptions.AttributeInferenceError as error:
                util.reraise(exceptions.InferenceError(**vars(error)))

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
            if node is util.Uninferable or not node.callable():
                continue
            for res in node.infer_call_result(caller, context):
                inferred = True
                yield res
        if not inferred:
            raise exceptions.InferenceError(node=self, caller=caller,
                                            context=context)

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
        except exceptions.AttributeInferenceError:
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
        context.callcontext = contextmod.CallContext(args=[self])

        try:
            result = _infer_method_result_truth(self, BOOL_SPECIAL_METHOD, context)
        except (exceptions.InferenceError, exceptions.AttributeInferenceError):
            # Fallback to __len__.
            try:
                result = _infer_method_result_truth(self, '__len__', context)
            except (exceptions.AttributeInferenceError, exceptions.InferenceError):
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
            return ((x is util.Uninferable and x or Instance(x)) for x in infer)
        return self._proxied.infer_call_result(caller, context)

    def bool_value(self):
        return True


class BoundMethod(UnboundMethod):
    """a special node representing a method bound to an instance"""
    # __func__ and __self__ are method-only special attributes, the
    # rest are general function special attributes.
    special_attributes = frozenset(
        ('__doc__', '__name__', '__qualname__', '__module__', '__defaults__',
         '__code__', '__globals__', '__dict__', '__closure__',
         '__annotations__', '__kwdefaults__', '__func__', '__self__'))

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
        # Verify the metaclass
        mcs = next(caller.args[0].infer(context=context))
        if not isinstance(mcs, scoped_nodes.ClassDef):
            # Not a valid first argument.
            return
        if not mcs.is_subtype_of("%s.type" % BUILTINS):
            # Not a valid metaclass.
            return

        # Verify the name
        name = next(caller.args[1].infer(context=context))
        if not isinstance(name, node_classes.Const):
            # Not a valid name, needs to be a const.
            return
        if not isinstance(name.value, str):
            # Needs to be a string.
            return

        # Verify the bases
        bases = next(caller.args[2].infer(context=context))
        if not isinstance(bases, node_classes.Tuple):
            # Needs to be a tuple.
            return
        inferred_bases = [next(elt.infer(context=context))
                          for elt in bases.elts]
        if not all(isinstance(base, scoped_nodes.ClassDef)
               for base in inferred_bases):
            # All the bases needs to be Classes
            return

        cls = mcs.__class__(name=name.value, lineno=caller.lineno,
                            col_offset=caller.col_offset,
                            parent=caller)

        # Verify the attributes.
        attrs = next(caller.args[3].infer(context=context))
        if not isinstance(attrs, node_classes.Dict):
            # Needs to be a dictionary.
            return
        body = []
        for key, value in attrs.items:
            key = next(key.infer(context=context))
            value = next(value.infer(context=context))
            if not isinstance(key, node_classes.Const):
                # Something invalid as an attribute.
                return
            if not isinstance(key.value, str):
                # Not a proper attribute.
                return
            assign = node_classes.Assign(parent=cls)
            assign.postinit(targets=node_classes.AssignName(key.value,
                                                            parent=assign),
                            value=value)
            body.append(assign)

        # Build the class from now.
        cls.postinit(bases=bases.elts, body=body, decorators=[],
                     newstyle=True, metaclass=mcs)
        return cls

    def infer_call_result(self, caller, context=None):
        if context is None:
            context = contextmod.InferenceContext()
        context = context.clone()
        context.boundnode = self.bound

        if (isinstance(self.bound, scoped_nodes.ClassDef)
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
    def __init__(self, parent):
        self.parent = parent
    
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

    @decorators.cachedproperty
    def _proxied(self):
        builtins = MANAGER.astroid_cache[BUILTINS]
        return builtins.getattr('generator')[0]
