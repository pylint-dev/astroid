# copyright 2003-2015 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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

"""Various context related utilities, including inference and call contexts."""
import contextlib
import itertools
import pprint

from astroid import exceptions
from astroid import util


class InferenceContext(object):
    __slots__ = ('path', 'lookupname', 'callcontext', 'boundnode', 'inferred')

    def __init__(self, path=None, inferred=None):
        self.path = path or set()
        self.lookupname = None
        self.callcontext = None
        self.boundnode = None
        self.inferred = inferred or {}

    def push(self, node):
        name = self.lookupname
        if (node, name) in self.path:
            return True

        self.path.add((node, name))
        return False

    def clone(self):
        # XXX copy lookupname/callcontext ?
        clone = InferenceContext(self.path, inferred=self.inferred)
        clone.callcontext = self.callcontext
        clone.boundnode = self.boundnode
        return clone

    def cache_generator(self, key, generator):
        results = []
        for result in generator:
            results.append(result)
            yield result

        self.inferred[key] = tuple(results)
        return

    @contextlib.contextmanager
    def restore_path(self):
        path = set(self.path)
        yield
        self.path = path

    def __str__(self):
        return '%s(%s)' % (type(self).__name__, ',\n    '.join(
            ('%s=%s' % (a, pprint.pformat(getattr(self, a), width=80-len(a)))
             for a in self.__slots__)))
    
    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, ', '.join(
            ('%s=%s' % (a, repr(getattr(self, a)))
             for a in self.__slots__)))


class CallContext(object):

    def __init__(self, args, keywords=None, starargs=None, kwargs=None):
        self.args = args
        if keywords:
            self.keywords = {arg.arg: arg.value for arg in keywords}
        else:
            self.keywords = {}

        self.starargs = starargs
        self.kwargs = kwargs

    @staticmethod
    def _infer_argument_container(container, key, context):
        its = []
        for inferred in container.infer(context=context):
            if inferred is util.YES:
                its.append((util.YES,))
                continue
            try:
                its.append(inferred.getitem(key, context).infer(context=context))
            except (exceptions.InferenceError, AttributeError):
                its.append((util.YES,))
            except (IndexError, TypeError):
                continue
        if its:
            return itertools.chain(*its)

    def infer_argument(self, funcnode, name, context, boundnode):
        """infer a function argument value according to the call context"""
        # 1. search in named keywords
        try:
            return self.keywords[name].infer(context)
        except KeyError:
            pass

        argindex = funcnode.args.find_argname(name)[0]
        if argindex is not None:
            # 2. first argument of instance/class method
            if argindex == 0 and funcnode.type in ('method', 'classmethod'):
                return iter((boundnode,))
            # if we have a method, extract one position
            # from the index, so we'll take in account
            # the extra parameter represented by `self` or `cls`
            if funcnode.type in ('method', 'classmethod'):
                argindex -= 1
            # 2. search arg index
            try:
                return self.args[argindex].infer(context)
            except IndexError:
                pass
            # 3. search in *args (.starargs)
            if self.starargs is not None:
                its = self._infer_argument_container(
                    self.starargs, argindex, context)
                if its:
                    return its
        # 4. Search in **kwargs
        if self.kwargs is not None:
            its = self._infer_argument_container(
                self.kwargs, name, context)
            if its:
                return its
        # 5. return default value if any
        try:
            return funcnode.args.default_value(name).infer(context)
        except exceptions.NoDefault:
            raise exceptions.InferenceError(name)


def copy_context(context):
    if context is not None:
        return context.clone()
    else:
        return InferenceContext()
