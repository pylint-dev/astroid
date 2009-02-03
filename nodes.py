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
 .as_string(), returning a string representation of the code (should be
  executable).

on From and Import :
 .real_name(name),

:author:    Sylvain Thenault
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com

DONE:
Assign
AugAssign
BinOp / (Add,Div,FloorDiv,Mod,Mul/Mult,Power/Pow,Sub,,Bitand,Bitor,Bitxor,
         LeftShift/LShift,RightShift/RShift)
BoolOp / (And,Or)
Break
Compare
Continue
Dict
Discard / Expr
Exec
For
Getattr / (Attribute)
Global
Import
From / ImportFrom
List
Module
Name
Pass
Print
Return
TryExcept
TryFinally
Tuple
UnaryOp / (UnaryAdd,UnarySub,Not)
Yield
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


from logilab.astng._exceptions import UnresolvableName, NotFoundError, InferenceError
from logilab.astng.utils import extend_class

INFER_NEED_NAME_STMTS = (From, Import, Global, TryExcept)
LOOP_SCOPES = COMPREHENSIONS_SCOPES + (For,)

import re
ID_RGX = re.compile('^[a-zA-Z_][a-zA-Z_0-9]*$')
del re

# astng fields definition ####################################################

Assert._astng_fields = ('test', 'fail',)
Assign._astng_fields = ('targets', 'value',)
AugAssign._astng_fields = ('target', 'value',)
BinOp._astng_fields = ('left', 'right',)
BoolOp._astng_fields = ('values',)
UnaryOp._astng_fields = ('operand',)

Backquote._astng_fields = ('value',)
Break._astng_fields = ()
CallFunc._astng_fields = ('func', 'args', 'starargs', 'kwargs')
Class._astng_fields = ('bases', 'body',) # name
Compare._astng_fields = ('left', 'ops',)
Const._astng_fields = ()
Continue._astng_fields = ()
Delete._astng_fields = ('targets', )
Dict._astng_fields = ('items',)
Discard._astng_fields = ('value',)
From._astng_fields = ()
EmptyNode._astng_fields = ()
ExceptHandler._astng_fields = ('type', 'name', 'body',) # XXX lineno & co inside._astng_fields instead of _attributes
Exec._astng_fields = ('expr', 'globals', 'locals',)
Function._astng_fields = ('decorators', 'body',)
For._astng_fields = ('target', 'iter', 'body', 'orelse',)
Getattr._astng_fields = ('expr',) # (former value), attr (now attrname), ctx
Global._astng_fields = ()
If._astng_fields = ('tests', 'orelse',)
Import._astng_fields = ()
Keyword._astng_fields = ('value',)
Lambda._astng_fields = ('body',)
List._astng_fields = ('elts',)  # ctx
ListComp._astng_fields = ('elt', 'generators')
ListCompFor._astng_fields = ('iter', 'ifs')
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
    fromlineno = None
    tolineno = None
    # parent node in the tree
    parent = None

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, getattr(self, 'name', ''))


    def get_children(self):
        d = self.__dict__
        for f in self._astng_fields:
            try:
                attr = d[f]
            except:
                print self, f
                raise
            if attr is None:
                continue
            if type(attr) is list:
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

    def next_sibling(self):
        """return the previous sibling statement 
        """
        while not self.is_statement: 
            self = self.parent
        index = self.parent.nodes.index(self)
        try:
            return self.parent.nodes[index+1]
        except IndexError:
            return

    def previous_sibling(self):
        """return the next sibling statement 
        """
        while not self.is_statement: 
            self = self.parent
        index = self.parent.nodes.index(self)
        if index > 0:
            return self.parent.nodes[index-1]
        return

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
        for child_node in self.getChildNodes():
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

extend_class(Node, NodeNG)

for klass in Break, Class, Continue, Discard, ExceptHandler, For, From, \
             Function, Global, If, Import, Return, \
             TryExcept, TryFinally, While, With, Yield:
    klass.is_statement = True


def const_factory(value):
    try:
        cls, value = CONST_VALUE_TRANSFORMS[value]
        node = cls(value)
    except KeyError:
        node = _const_factory(value)
    return node

def stmts_as_string(node, attr='body'):
    """return an ast.Stmt node as string"""
    stmts = '\n'.join([n.as_string() for n in getattr(node, attr)])
    if isinstance(node, Module):
        return stmts
    return '    ' + stmts.replace('\n', '\n    ')

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
    for cond, stmts in node.tests:
        yield cond
        for stmt in stmts:
            yield stmt
    for stmt in node.orelse:
        yield stmt

If.get_children = _if_get_children

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

# as_string ###################################################################

def assert_as_string(node):
    """return an ast.Assert node as string"""
    if node.fail:
        return 'assert %s, %s' % (node.test.as_string(), node.fail.as_string())
    return 'assert %s' % node.test.as_string()
Assert.as_string = assert_as_string

def assign_as_string(node):
    """return an ast.Assign node as string"""
    lhs = ' = '.join([n.as_string() for n in node.targets])
    return '%s = %s' % (lhs, node.value.as_string())
Assign.as_string = assign_as_string

def augassign_as_string(node):
    """return an ast.AugAssign node as string"""
    return '%s %s %s' % (node.target.as_string(), node.op, node.value.as_string())
AugAssign.as_string = augassign_as_string

def backquote_as_string(node):
    """return an ast.Backquote node as string"""
    return '`%s`' % node.expr.as_string()
Backquote.as_string = backquote_as_string

def binop_as_string(node):
    """return an ast.BinOp node as string"""
    return '(%s) %s (%s)' % (node.left.as_string(), node.op, node.right.as_string())
BinOp.as_string = binop_as_string

def boolop_as_string(node):
    """return an ast.BoolOp node as string"""
    return (' %s ' % node.op).join(['(%s)' % n.as_string() for n in node.values])
BoolOp.as_string = boolop_as_string

def break_as_string(node):
    """return an ast.Break node as string"""
    return 'break'
Break.as_string = break_as_string

def callfunc_as_string(node):
    """return an ast.CallFunc node as string"""
    expr_str = node.node.as_string()
    args = ', '.join([arg.as_string() for arg in node.args])
    if node.star_args:
        args += ', *%s' % node.star_args.as_string()
    if node.dstar_args:
        args += ', **%s' % node.dstar_args.as_string()
    return '%s(%s)' % (expr_str, args)
CallFunc.as_string = callfunc_as_string

def class_as_string(node):
    """return an ast.Class node as string"""
    bases =  ', '.join([n.as_string() for n in node.bases])
    bases = bases and '(%s)' % bases or ''
    docs = node.doc and '\n    """%s"""' % node.doc or ''
    return 'class %s%s:%s\n    %s\n' % (node.name, bases, docs,
                                        node.code.as_string())
Class.as_string = class_as_string

def compare_as_string(node):
    """return an ast.Compare node as string"""
    rhs_str = ' '.join(['%s %s' % (op, expr.as_string())
                        for op, expr in node.ops])
    return '%s %s' % (node.left.as_string(), rhs_str)
Compare.as_string = compare_as_string

def continue_as_string(node):
    """return an ast.Continue node as string"""
    return 'continue'
Continue.as_string = continue_as_string

def delete_as_string(node): # XXX check if correct
    """return an ast.Delete node as string"""
    return 'del %s' % ', '.join([child.as_string() for child in node.targets])

def dict_as_string(node):
    """return an ast.Dict node as string"""
    return '{%s}' % ', '.join(['%s: %s' % (key.as_string(), value.as_string())
                               for key, value in node.items])
Dict.as_string = dict_as_string

def discard_as_string(node):
    """return an ast.Discard node as string"""
    return node.expr.as_string()
Discard.as_string = discard_as_string

def excepthandler_as_string(node):
    if node.type:
        if node.name:
            excs = 'except %s, %s' % (node.type.as_string(),
                                      node.name.as_string())
        else:
            excs = 'except %s' % node.type.as_string()
    else:
        excs = 'except'
    return '%s:\n%s' % (excs, stmts_as_string(node))
ExceptHandler.as_string = excepthandler_as_string

def ellipsis_as_string(node):
    """return an ast.Ellipsis node as string"""
    return '...'
Ellipsis.as_string = ellipsis_as_string

def exec_as_string(node):
    """return an ast.Exec node as string"""
    if node.locals:
        return 'exec %s in %s, %s' % (node.expr.as_string(),
                                      node.globals.as_string(),
                                      node.locals.as_string())
    if node.globals:
        return 'exec %s in %s' % (node.expr.as_string(),
                                  node.globals.as_string())
    return 'exec %s' % node.expr.as_string()
Exec.as_string = exec_as_string

def for_as_string(node):
    """return an ast.For node as string"""
    fors = 'for %s in %s:\n%s' % (node.target.as_string(),
                                  node.iter.as_string(),
                                  stmts_as_string(node))
    if node.orelse:
        fors = '%s\nelse:\n    %s' % (fors, node.orelse.as_string())
    return fors
For.as_string = for_as_string

def from_as_string(node):
    """return an ast.From node as string"""
    # XXX level
    return 'from %s import %s' % (node.modname, _import_string(node.names))
From.as_string = from_as_string

def function_as_string(node):
    """return an ast.Function node as string"""
    fargs = node.format_args()
    docs = node.doc and '\n    """%s"""' % node.doc or ''
    return 'def %s(%s):%s\n    %s' % (node.name, fargs, docs,
                                      node.code.as_string())
Function.as_string = function_as_string

def genexpr_as_string(node):
    """return an ast.GenExpr node as string"""
    return '(%s)' % node.code.as_string()
GenExpr.as_string = genexpr_as_string

def getattr_as_string(node):
    """return an ast.Getattr node as string"""
    return '%s.%s' % (node.expr.as_string(), node.attrname)
Getattr.as_string = getattr_as_string

def global_as_string(node):
    """return an ast.Global node as string"""
    return 'global %s' % ', '.join(node.names)
Global.as_string = global_as_string

def if_as_string(node):
    """return an ast.If node as string"""
    cond, body = node.tests[0]
    ifs = ['if %s:\n    %s' % (cond.as_string(), body.as_string())]
    for cond, body in node.tests[1:]:
        ifs.append('elif %s:\n    %s' % (cond.as_string(), body.as_string()))
    if node.else_:
        ifs.append('else:\n    %s' % node.else_.as_string())
    return '\n'.join(ifs)
If.as_string = if_as_string

def import_as_string(node):
    """return an ast.Import node as string"""
    return 'import %s' % _import_string(node.names)
Import.as_string = import_as_string

def invert_as_string(node):
    """return an ast.Invert node as string"""
    return '~%s' % node.expr.as_string()
Invert.as_string = invert_as_string

def lambda_as_string(node):
    """return an ast.Lambda node as string"""
    return 'lambda %s: %s' % (node.format_args(), node.code.as_string())
Lambda.as_string = lambda_as_string

def list_as_string(node):
    """return an ast.List node as string"""
    return '[%s]' % ', '.join([child.as_string() for child in node.elts])
List.as_string = list_as_string

def listcomp_as_string(node):
    """return an ast.ListComp node as string"""
    return '[%s %s]' % (node.expr.as_string(), ' '.join([n.as_string()
                                                         for n in node.quals]))
ListComp.as_string = listcomp_as_string

def module_as_string(node):
    """return an ast.Module node as string"""
    docs = node.doc and '"""%s"""\n' % node.doc or ''
    return '%s%s' % (docs, stmts_as_string(node))
Module.as_string = module_as_string

def name_as_string(node):
    """return an ast.Name node as string"""
    return node.name
Name.as_string = name_as_string

def pass_as_string(node):
    """return an ast.Pass node as string"""
    return 'pass'
Pass.as_string = pass_as_string

def print_as_string(node):
    """return an ast.Print node as string"""
    nodes = ', '.join([n.as_string() for n in node.values])
    if node.dest:
        return 'print >> %s, %s,' % (node.dest.as_string(), nodes)
    return 'print %s,' % nodes
Print.as_string = print_as_string

def raise_as_string(node):
    """return an ast.Raise node as string"""
    if node.expr1:
        if node.expr2:
            if node.expr3:
                return 'raise %s, %s, %s' % (node.expr1.as_string(),
                                             node.expr2.as_string(),
                                             node.expr3.as_string())
            return 'raise %s, %s' % (node.expr1.as_string(),
                                     node.expr2.as_string())
        return 'raise %s' % node.expr1.as_string()
    return 'raise'
Raise.as_string = raise_as_string

def return_as_string(node):
    """return an ast.Return node as string"""
    return 'return %s' % node.value.as_string()
Return.as_string = return_as_string

def slice_as_string(node):
    """return an ast.Slice node as string"""
    # FIXME: use flags
    lower = node.lower and node.lower.as_string() or ''
    upper = node.upper and node.upper.as_string() or ''
    return '%s[%s:%s]' % (node.expr.as_string(), lower, upper)
Slice.as_string = slice_as_string

def subscript_as_string(node):
    """return an ast.Subscript node as string"""
    # FIXME: flags ?
    return '%s[%s]' % (node.expr.as_string(), ','.join([n.as_string()
                                                        for n in node.subs]))
Subscript.as_string = subscript_as_string

def tryexcept_as_string(node):
    """return an ast.TryExcept node as string"""
    trys = ['try:\n%s' % stmts_as_string(node)]
    for handler in node.handlers:
        trys.append(handler.as_string())
    if node.orelse:
        trys.append('else:\n%s' % stmts_as_string(node, 'orelse'))
    return '\n'.join(trys)
TryExcept.as_string = tryexcept_as_string

def tryfinally_as_string(node):
    """return an ast.TryFinally node as string"""
    return 'try:\n%s\nfinally:\n%s' % (stmts_as_string(node),
                                       stmts_as_string(node, 'finalbody'))
TryFinally.as_string = tryfinally_as_string

def tuple_as_string(node):
    """return an ast.Tuple node as string"""
    return '(%s)' % ', '.join([child.as_string() for child in node.elts])
Tuple.as_string = tuple_as_string

def unaryop_as_string(node):
    """return an ast.UnaryOp node as string"""
    return '%s%s' % (node.op, node.operant.as_string())
UnaryOp.as_string = unaryop_as_string

def while_as_string(node):
    """return an ast.While node as string"""
    whiles = 'while %s:\n%s' % (node.test.as_string(), stmts_as_string(node))
    if node.orelse:
        whiles = '%s\nelse:\n%s' % (whiles, stmts_as_string(node, 'orelse'))
    return whiles
While.as_string = while_as_string

def with_as_string(node):
    """return an ast.With node as string"""
    withs = 'with (%s) as (%s):\n    %s' % (node.expr.as_string(),
                                      node.vars.as_string(),
                                      node.body.as_string())
    return withs
With.as_string = with_as_string

def yield_as_string(node):
    """yield an ast.Yield node as string"""
    return 'yield %s' % node.value.as_string()
Yield.as_string = yield_as_string


def _import_string(names):
    """return a list of (name, asname) formatted as a string"""
    _names = []
    for name, asname in names:
        if asname is not None:
            _names.append('%s as %s' % (name, asname))
        else:
            _names.append(name)
    return  ', '.join(_names)


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
    def __init__(self, proxied=None):
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
    __str__ = __repr__
    
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
    __str__ = as_string = __repr__
    
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
    __str__ = as_string = __repr__

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

def infer_end(self, context=None):
    """inference's end for node such as Module, Class, Function, Const...
    """
    yield self

def end_ass_type(self):
    return self

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
