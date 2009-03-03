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
"""
on all nodes :
 .is_statement, returning true if the node should be considered as a
  statement node
 .root(), returning the root node of the tree (i.e. a Module)
 .previous_sibling(), returning previous sibling statement node
 .next_sibling(), returning next sibling statement node
 .statement(), returning the first parent node marked as statement node
 .frame(), returning the first node defining a new local scope (i.e.
  Module, Function or Class)
 .set_local(name, node), define an identifier <name> on the first parent frame,
  with the node defining it. This is used by the astng builder and should not
  be used from out there.

on From and Import :
 .real_name(name),

:author:    Sylvain Thenault
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com

"""

from __future__ import generators

__docformat__ = "restructuredtext en"

from itertools import imap

try:
    from logilab.astng._nodes_ast import *
    from logilab.astng._nodes_ast import _const_factory
    AST_MODE = '_ast'
except ImportError:
    from logilab.astng._nodes_compiler import *
    from logilab.astng._nodes_compiler import _const_factory
    AST_MODE = 'compiler'


from logilab.astng._exceptions import UnresolvableName, NotFoundError, \
                                        InferenceError, ASTNGError
from logilab.astng.utils import extend_class, REDIRECT

INFER_NEED_NAME_STMTS = (From, Import, Global, TryExcept)
LOOP_SCOPES = (Comprehension, For,)

import re
ID_RGX = re.compile('^[a-zA-Z_][a-zA-Z_0-9]*$')
del re

# astng fields definition ####################################################
AssAttr._astng_fields = ('expr',)
Assert._astng_fields = ('test', 'fail',)
Assign._astng_fields = ('targets', 'value',)
AssName._astng_fields = ()

AugAssign._astng_fields = ('target', 'value',)
BinOp._astng_fields = ('left', 'right',)
BoolOp._astng_fields = ('values',)
UnaryOp._astng_fields = ('operand',)

Backquote._astng_fields = ('value',)
Break._astng_fields = ()
CallFunc._astng_fields = ('func', 'args', 'starargs', 'kwargs')
Class._astng_fields = ('bases', 'body',) # name
Compare._astng_fields = ('left', 'ops',)
Comprehension._astng_fields = ('target', 'iter' ,'ifs')
Const._astng_fields = ()
Continue._astng_fields = ()
Decorators._astng_fields = ('items',)
Delete._astng_fields = ('targets', )
DelAttr._astng_fields = ('expr',)
DelName._astng_fields = ()
Dict._astng_fields = ('items',)
Discard._astng_fields = ('value',)
From._astng_fields = ()
EmptyNode._astng_fields = ()
ExceptHandler._astng_fields = ('type', 'name', 'body',) # XXX lineno & co inside._astng_fields instead of _attributes
Exec._astng_fields = ('expr', 'globals', 'locals',)
Function._astng_fields = ('decorators', 'defaults', 'body') # XXX argnames ?
For._astng_fields = ('target', 'iter', 'body', 'orelse',)
Getattr._astng_fields = ('expr',) # (former value), attr (now attrname), ctx
GenExpr._astng_fields = ('elt', 'generators')
Global._astng_fields = ()
If._astng_fields = ('tests', 'orelse',)
Import._astng_fields = ()
Keyword._astng_fields = ('value',)
Lambda._astng_fields = ('body',)
List._astng_fields = ('elts',)  # ctx
ListComp._astng_fields = ('elt', 'generators')
Module._astng_fields = ('body',)
Name._astng_fields = () # id, ctx
Pass._astng_fields = ()
Print._astng_fields = ('dest', 'values',) # nl
Raise._astng_fields = ('type', 'inst', 'tback')
Return._astng_fields = ('value',)
Subscript._astng_fields = ('expr', 'subs',) # value, slice
TryExcept._astng_fields = ('body', 'handlers', 'orelse',)
TryFinally._astng_fields = ('body', 'finalbody',)
Tuple._astng_fields = ('elts',)  # ctx
With._astng_fields = ('expr', 'vars', 'body')
While._astng_fields = ('test', 'body', 'orelse',)
Yield._astng_fields = ('value',)


# Node  ######################################################################

class NodeNG:
    """/!\ this class should not be used directly /!\
    It is used as method and attribute container, and updates the
    original class from the compiler.ast / _ast module using its dictionnary
    (see below the class definition)
    """
    is_statement = False
    # attributes below are set by the builder module or by raw factories
    lineno = None
    fromlineno = None
    tolineno = None
    # parent node in the tree
    parent = None

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, getattr(self, 'name', ''))

    def accept(self, visitor):
        klass = self.__class__.__name__
        func = getattr(visitor, "visit_" + REDIRECT.get(klass, klass).lower() )
        return func(self)

    def get_children(self):
        d = self.__dict__
        for f in self._astng_fields:
            attr = d[f]
            if attr is None:
                continue
            if isinstance(attr, (list, tuple)):
                for elt in attr:
                    yield elt
            else:
                yield attr

    def parent_of(self, node):
        """return true if i'm a parent of the given node"""
        parent = node.parent
        while parent is not None:
            if self is parent:
                return True
            parent = parent.parent
        return False

    def statement(self):
        """return the first parent node marked as statement node
        """
        if self.is_statement:
            return self
        return self.parent.statement()

    def frame(self):
        """return the first parent frame node (i.e. Module, Function or Class)
        """
        return self.parent.frame()

    def scope(self):
        """return the first node defining a new scope (i.e. Module,
        Function, Class, Lambda but also GenExpr)
        """
        try:
            return self.parent.scope()
        except AttributeError:
            print self, self.parent
            raise

    def root(self):
        """return the root node of the tree, (i.e. a Module)
        """
        if self.parent:
            return self.parent.root()
        return self


    def next_sibling(self, attr = "body"):# FIXME : what do we want ?
        """return the previous sibling statement
        """
        stmts = getattr(self.statement(), attr)
        for k, stmt in enumerate(stmts[:-1]):
            if self is stmt:
                return stmts[k+1]


    def previous_sibling(self, attr = "body"): # FIXME : what do we want ?
        """return the next sibling statement 
        """
        stmts = getattr(self.statement(), attr)
        for k, stmt in enumerate(stmts[1:]):
            if self is stmt:
                return stmts[k]

    def nearest(self, nodes):
        """return the node which is the nearest before this one in the
        given list of nodes
        """
        myroot = self.root()
        mylineno = self.source_line()
        nearest = None, 0
        for node in nodes:
            assert node.root() is myroot, \
                   'not from the same module %s' % (self, node)
            lineno = node.source_line()
            if node.source_line() > mylineno:
                break
            if lineno > nearest[1]:
                nearest = node, lineno
        # FIXME: raise an exception if nearest is None ?
        return nearest[0]

    def source_line(self):
        """return the line number where the given node appears

        we need this method since not all nodes have the lineno attribute
        correctly set...
        """
        line = self.lineno
        if line is None:
            _node = self
            try:
                while line is None:
                    _node = _node.get_children().next()
                    line = _node.lineno
            except StopIteration:
                _node = self.parent
                while _node and line is None:
                    line = _node.lineno
                    _node = _node.parent
            self.lineno = line
        return line
    
    def last_source_line(self):
        """return the last block line number for this node (i.e. including
        children)
        """
        try:
            return self.__dict__['_cached_last_source_line']
        except KeyError:
            line = self.source_line()
            # XXX the latest children would be enough, no ?
            for node in self.get_children():
                line = max(line, node.last_source_line())
            self._cached_last_source_line = line
            return line

    def block_range(self, lineno):
        """handle block line numbers range for non block opening statements
        """
        return lineno, self.last_source_line()

    def set_local(self, name, stmt):
        """delegate to a scoped parent handling a locals dictionary
        """
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
        if isinstance(self, INFER_NEED_NAME_STMTS) or (
                 isinstance(self, (Function, Lambda)) and self is frame):
            return name
        return None

    def eq(self, value):
        return False
    
    def as_string(self):
        from logilab.astng.nodes_as_string import as_string
        return as_string(self)
        
extend_class(Node, NodeNG)


for klass in (Assign, Break, Class, Continue, Delete, Discard, ExceptHandler,
              For, From, Function, Global, If, Import, Print, Return,
              TryExcept, TryFinally, While, With, Yield):
    klass.is_statement = True

CONST_CLS = {
    list: List,
    tuple: Tuple,
    dict: Dict,
    }
    
def const_factory(value):
    """return an astng node for a python value"""
    try:
        # if value is of class list, tuple, dict use specific class, not Const
        cls = CONST_CLS[value.__class__]
        return cls()
    except KeyError:
        pass
    try:
        cls, value = CONST_VALUE_TRANSFORMS[value]
        node = cls(value)
    except KeyError:
        node = _const_factory(value)
    return node

def _get_children_nochildren(self):
    return ()

#  get_children overrides  ####################################################

def _dict_get_children(node): # XXX : distinguish key and value ?
    """override get_children for Dict"""
    for key, value in node.items:
        yield key
        yield value
Dict.get_children = _dict_get_children

def _if_get_children(node):
    """get children looping into body lists"""
    for cond, stmts in node.tests:
        yield cond
        for stmt in stmts:
            yield stmt
    for stmt in node.orelse:
        yield stmt

If.get_children = _if_get_children

def _subscript_get_children(node):
    """get_children by removing None children"""
    yield node.expr
    for sub in node.subs:
        if sub:
            yield sub
Subscript.get_children = _subscript_get_children


def _compare_get_children(node):
    """override get_children for tuple fields"""
    yield node.left
    for op, comparator in node.ops:
        yield comparator # we don't want the 'op'
Compare.get_children = _compare_get_children

# block range overrides #######################################################

def object_block_range(node, lineno):
    """handle block line numbers range for function/class statements:

    start from the "def" or "class" position whatever the given lineno
    """
    return node.source_line(), node.last_source_line()

Function.block_range = object_block_range
Class.block_range = object_block_range
Module.block_range = object_block_range

# XXX only if compiler mode ?
def if_block_range(node, lineno):
    """handle block line numbers range for if/elif statements
    """
    last = None
    for test, testbody in node.tests[1:]:
        if lineno == testbody.source_line():
            return lineno, lineno
        if lineno <= testbody.last_source_line():
            return lineno, testbody.last_source_line()
        if last is None:
            last = testbody.source_line() - 1
    return elsed_block_range(node, lineno, last)

If.block_range = if_block_range

def try_except_block_range(node, lineno):
    """handle block line numbers range for try/except statements
    """
    last = None
    for excls, exinst, exbody in node.handlers:
        if excls and lineno == excls.source_line():
            return lineno, lineno
        if exbody.source_line() <= lineno <= exbody.last_source_line():
            return lineno, exbody.last_source_line()
        if last is None:
            last = exbody.source_line() - 1
    return elsed_block_range(node, lineno, last)

TryExcept.block_range = try_except_block_range

def elsed_block_range(node, lineno, last=None):
    """handle block line numbers range for try/finally, for and while
    statements
    """
    if lineno == node.source_line():
        return lineno, lineno
    if node.else_:
        if lineno >= node.else_.source_line():
            return lineno, node.else_.last_source_line()
        return lineno, node.else_.source_line() - 1
    return lineno, last or node.last_source_line()

TryFinally.block_range = elsed_block_range
While.block_range = elsed_block_range
For.block_range = elsed_block_range

# From and Import #############################################################

def real_name(node, asname):
    """get name from 'as' name"""
    for index in range(len(node.names)):
        name, _asname = node.names[index]
        if name == '*':
            return asname
        if not _asname:
            name = name.split('.', 1)[0]
            _asname = name
        if asname == _asname:
            return name
    raise NotFoundError(asname)
    
From.real_name = real_name
Import.real_name = real_name

def infer_name_module(node, name):
    context = InferenceContext(node)
    context.lookupname = name
    return node.infer(context, asname=False)
Import.infer_name_module = infer_name_module


# special inference objects ###################################################

class Yes(object):
    """a yes object"""
    def __repr__(self):
        return 'YES'
    def __getattribute__(self, name):
        return self
    def __call__(self, *args, **kwargs):
        return self

YES = Yes()

class Proxy(Proxy_):
    """a simple proxy object"""
    _proxied = None
    
    def __init__(self, proxied=None):
        if proxied is not None:
            self._proxied = proxied

    def __getattr__(self, name):
        if name == '_proxied':
            return getattr(self.__class__, '_proxied')
        #assert self._proxied is not self
        #assert getattr(self._proxied, name) is not self
        return getattr(self._proxied, name)

    def infer(self, context=None):
        yield self

class InstanceMethod(Proxy):
    """a special node representing a function bound to an instance"""
    def __repr__(self):
        instance = self._proxied.parent.frame()
        return '<Bound method %s of %s.%s at 0x%s' % (self._proxied.name,
                                                      instance.root().name,
                                                      instance.name,
                                                      id(self))
    __str__ = __repr__

    def is_bound(self):
        return True


class Instance(Proxy):
    """a special node representing a class instance"""
    def getattr(self, name, context=None, lookupclass=True):
        try:
            return self._proxied.instance_attr(name, context)
        except NotFoundError:
            if name == '__class__':
                return [self._proxied]
            if name == '__name__':
                # access to __name__ gives undefined member on class
                # instances but not on class objects
                raise NotFoundError(name)
            if lookupclass:
                return self._proxied.getattr(name, context)
        raise NotFoundError(name)

    def igetattr(self, name, context=None):
        """infered getattr"""
        try:
            # XXX frame should be self._proxied, or not ?
            return _infer_stmts(
                self._wrap_attr(self.getattr(name, context, lookupclass=False)),
                                context, frame=self)
        except NotFoundError:
            try:
                # fallback to class'igetattr since it has some logic to handle
                # descriptors
                return self._wrap_attr(self._proxied.igetattr(name, context))
            except NotFoundError:
                raise InferenceError(name)
            
    def _wrap_attr(self, attrs):
        """wrap bound methods of attrs in a InstanceMethod proxies"""
        # Guess which attrs are used in inference.
        def wrap(attr):
            if isinstance(attr, Function) and attr.type == 'method':
                return InstanceMethod(attr)
            else:
                return attr
        return imap(wrap, attrs)
        
    def infer_call_result(self, caller, context=None):
        """infer what's a class instance is returning when called"""
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
    
class Generator(Proxy): 
    """a special node representing a generator"""
    def callable(self):
        return True
    
    def pytype(self):
        return '__builtin__.generator'

# additional nodes  ##########################################################

class NoneType(Instance, NodeNG):
    """None value (instead of Name('None')"""
    _proxied_class = None.__class__
    _proxied = None
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return 'None'
    def get_children(self):
        return ()
    __str__ = __repr__
    
class Bool(Instance, NodeNG):
    """None value (instead of Name('True') / Name('False')"""
    _proxied_class = bool
    _proxied = None
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return str(self.value)
    def get_children(self):
        return ()
    __str__ = __repr__

CONST_NAME_TRANSFORMS = {'None': (NoneType, None),
                         'True': (Bool, True),
                         'False': (Bool, False)}
CONST_VALUE_TRANSFORMS = {None: (NoneType, None),
                          True: (Bool, True),
                          False: (Bool, False)}


# inference utilities #########################################################

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

def _infer_stmts(stmts, context, frame=None):
    """return an iterator on statements infered by each statement in <stmts>
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

def repr_tree(node, indent='', _done=None):
    if _done is None:
        _done = set()
    if node in _done:
        print ('loop in tree: %r (%s)' % (node, node.lineno))
        return
    _done.add(node)
    print indent + repr(node)
    indent += ' '
    for child in node.get_children():
        repr_tree(child, indent, _done)
