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
"""Inference utilities

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""
from __future__ import generators

__doctype__ = "restructuredtext en"

from logilab.common.compat import chain, imap

from logilab.astng._exceptions import InferenceError, NotFoundError, UnresolvableName
from logilab.astng._nodes import BaseClass


class Proxy(BaseClass):
    """a simple proxy object"""
    _proxied = None

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


class InferenceContext(object):
    __slots__ = ('startingfrom', 'path', 'lookupname', 'callcontext', 'boundnode')

    def __init__(self, node=None, path=None):
        self.startingfrom = node # XXX useful ?
        if path is None:
            self.path = []
        else:
            self.path = path
        self.lookupname = None
        self.callcontext = None
        self.boundnode = None

    def push(self, node):
        name = self.lookupname
        if (node, name) in self.path:
            raise StopIteration()
        self.path.append( (node, name) )

    def pop(self):
        return self.path.pop()

    def clone(self):
        # XXX copy lookupname/callcontext ?
        clone = InferenceContext(self.startingfrom, self.path)
        clone.callcontext = self.callcontext
        clone.boundnode = self.boundnode
        return clone

def copy_context(context):
    if context is not None:
        return context.clone()
    else:
        return InferenceContext()

def _infer_stmts(stmts, context, frame=None):
    """return an iterator on statements inferred by each statement in <stmts>
    """
    stmt = None
    infered = False
    if context is not None:
        name = context.lookupname
        context = context.clone()
    else:
        name = None
        context = InferenceContext()
    for stmt in stmts:
        if stmt is YES:
            yield stmt
            infered = True
            continue
        context.lookupname = stmt._infer_name(frame, name)
        try:
            for infered in stmt.infer(context):
                yield infered
                infered = True
        except UnresolvableName:
            continue
        except InferenceError:
            yield YES
            infered = True
    if not infered:
        raise InferenceError(str(stmt))

class _Yes(object):
    """a yes object"""
    def __repr__(self):
        return 'YES'
    def __getattribute__(self, name):
        if name.startswith('__') and name.endswith('__'):
            # to avoid inspection pb
            return super(_Yes, self).__getattribute__(name)
        return self
    def __call__(self, *args, **kwargs):
        return self


# decorators ##################################################################

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

def yes_if_nothing_infered(func):
    def wrapper(*args, **kwargs):
        infered = False
        for node in func(*args, **kwargs):
            infered = True
            yield node
        if not infered:
            yield YES
    return wrapper

def raise_if_nothing_infered(func):
    def wrapper(*args, **kwargs):
        infered = False
        for node in func(*args, **kwargs):
            infered = True
            yield node
        if not infered:
            raise InferenceError()
    return wrapper


# special inference objects (e.g. may be returned as nodes by .infer()) #######

YES = _Yes()


class Instance(Proxy):
    """a special node representing a class instance"""
    def getattr(self, name, context=None, lookupclass=True):
        try:
            values = self._proxied.instance_attr(name, context)
        except NotFoundError:
            if name == '__class__':
                return [self._proxied]
            if lookupclass:
                # class attributes not available through the instance
                # unless they are explicitly defined
                if name in ('__name__', '__bases__', '__mro__'):
                    return self._proxied.local_attr(name)
                return self._proxied.getattr(name, context)
            raise NotFoundError(name)
        # since we've no context information, return matching class members as
        # well
        if lookupclass:
            try:
                return values + self._proxied.getattr(name, context)
            except NotFoundError:
                pass
        return values

    def igetattr(self, name, context=None):
        """inferred getattr"""
        try:
            # XXX frame should be self._proxied, or not ?
            return _infer_stmts(
                self._wrap_attr(self.getattr(name, context, lookupclass=False), context),
                                context, frame=self)
        except NotFoundError:
            try:
                # fallback to class'igetattr since it has some logic to handle
                # descriptors
                return self._wrap_attr(self._proxied.igetattr(name, context), context)
            except NotFoundError:
                raise InferenceError(name)

    def _wrap_attr(self, attrs, context=None):
        """wrap bound methods of attrs in a InstanceMethod proxies"""
        for attr in attrs:
            if isinstance(attr, UnboundMethod):
                if '__builtin__.property' in attr.decoratornames():
                    for infered in attr.infer_call_result(self, context):
                        yield infered
                elif attr.type in ('method', 'classmethod'):
                    # XXX could get some information from the bound node:
                    #     self (if method) or self._proxied (if class method)
                    yield BoundMethod(attr)
                else:
                    yield attr
            else:
                yield attr

    def infer_call_result(self, caller, context=None):
        """infer what a class instance is returning when called"""
        infered = False
        for node in self._proxied.igetattr('__call__', context):
            for res in node.infer_call_result(caller, context):
                infered = True
                yield res
        if not infered:
            raise InferenceError()

    def __repr__(self):
        return '<Instance of %s.%s at 0x%s>' % (self._proxied.root().name,
                                                self._proxied.name,
                                                id(self))
    def __str__(self):
        return 'Instance of %s.%s' % (self._proxied.root().name,
                                      self._proxied.name)

    def callable(self):
        try:
            self._proxied.getattr('__call__')
            return True
        except NotFoundError:
            return False

    def pytype(self):
        return self._proxied.qname()


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
        return super(UnboundMethod, self).getattr(name, context)

    def igetattr(self, name, context=None):
        if name == 'im_func':
            return iter((self._proxied,))
        return super(UnboundMethod, self).igetattr(name, context)


class BoundMethod(UnboundMethod):
    """a special node representing a method bound to an instance"""
    def is_bound(self):
        return True


class Generator(Proxy):
    """a special node representing a generator"""
    def callable(self):
        return True

    def pytype(self):
        return '__builtin__.generator'


