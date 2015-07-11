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
"""this module contains utilities for rebuilding a _ast tree in
order to get a single Astroid representation
"""
import sys
from _ast import (
    Expr, Str,
    # binary operators
    Add, BinOp, Div, FloorDiv, Mod, Mult, Pow, Sub, BitAnd, BitOr, BitXor,
    LShift, RShift,
    # logical operators
    And, Or,
    # unary operators
    UAdd, USub, Not, Invert,
    # comparison operators
    Eq, Gt, GtE, In, Is, IsNot, Lt, LtE, NotEq, NotIn,
    )

from astroid import nodes as new
from astroid import astpeephole

_BIN_OP_CLASSES = {Add: '+',
                   BitAnd: '&',
                   BitOr: '|',
                   BitXor: '^',
                   Div: '/',
                   FloorDiv: '//',
                   Mod: '%',
                   Mult: '*',
                   Pow: '**',
                   Sub: '-',
                   LShift: '<<',
                   RShift: '>>',
                  }
if sys.version_info >= (3, 5):
    from _ast import MatMult
    _BIN_OP_CLASSES[MatMult] = '@'

_BOOL_OP_CLASSES = {And: 'and',
                    Or: 'or',
                   }

_UNARY_OP_CLASSES = {UAdd: '+',
                     USub: '-',
                     Not: 'not',
                     Invert: '~',
                    }

_CMP_OP_CLASSES = {Eq: '==',
                   Gt: '>',
                   GtE: '>=',
                   In: 'in',
                   Is: 'is',
                   IsNot: 'is not',
                   Lt: '<',
                   LtE: '<=',
                   NotEq: '!=',
                   NotIn: 'not in',
                  }

CONST_NAME_TRANSFORMS = {'None':  None,
                         'True':  True,
                         'False': False,
                        }

REDIRECT = {'arguments': 'Arguments',
            'comprehension': 'Comprehension',
            "ListCompFor": 'Comprehension',
            "GenExprFor": 'Comprehension',
            'excepthandler': 'ExceptHandler',
            'keyword': 'Keyword',
           }
PY3 = sys.version_info >= (3, 0)
PY34 = sys.version_info >= (3, 4)

def _init_set_doc(node, newnode):
    newnode.doc = None
    try:
        if isinstance(node.body[0], Expr) and isinstance(node.body[0].value, Str):
            newnode.doc = node.body[0].value.s
            node.body = node.body[1:]

    except IndexError:
        pass # ast built from scratch


def _create_yield_node(node, parent, rebuilder, factory, assign_ctx):
    newnode = factory()
    _lineno_parent(node, newnode, parent)
    if node.value is not None:
        newnode.value = rebuilder.visit(node.value, newnode, assign_ctx)
    return newnode


def _lineno_parent(oldnode, newnode, parent):
    newnode.parent = parent
    newnode.lineno = oldnode.lineno
    newnode.col_offset = oldnode.col_offset

def _set_infos(oldnode, newnode, parent):
    newnode.parent = parent
    if hasattr(oldnode, 'lineno'):
        newnode.lineno = oldnode.lineno
    if hasattr(oldnode, 'col_offset'):
        newnode.col_offset = oldnode.col_offset


class TreeRebuilder(object):
    """Rebuilds the _ast tree to become an Astroid tree"""

    def __init__(self, manager):
        self._manager = manager
        self._global_names = []
        self._from_nodes = []
        self._delayed_assattr = []
        self._visit_meths = {}
        self._transform = manager.transform
        self._peepholer = astpeephole.ASTPeepholeOptimizer()

    def visit_module(self, node, modname, modpath, package):
        """visit a Module node by returning a fresh instance of it"""
        newnode = new.Module(modname, None, modpath, modpath,
                             package=package, parent=None)
        _init_set_doc(node, newnode)
        newnode.postinit([self.visit(child, newnode) for child in node.body])
        return self._transform(newnode)

    def visit(self, node, parent, assign_ctx=None):
        cls = node.__class__
        if cls in self._visit_meths:
            visit_method = self._visit_meths[cls]
        else:
            cls_name = cls.__name__
            visit_name = 'visit_' + REDIRECT.get(cls_name, cls_name).lower()
            visit_method = getattr(self, visit_name)
            self._visit_meths[cls] = visit_method
        return self._transform(visit_method(node, parent, assign_ctx))

    def _save_assignment(self, node, name=None):
        """save assignement situation since node.parent is not available yet"""
        if self._global_names and node.name in self._global_names[-1]:
            node.root().set_local(node.name, node)
        else:
            node.parent.set_local(node.name, node)


    def visit_arguments(self, node, parent, assign_ctx=None,
                        kwonlyargs=None, kw_defaults=None, annotations=None):
        """visit a Arguments node by returning a fresh instance of it"""
        vararg, kwarg = node.vararg, node.kwarg
        if PY34:
            newnode = new.Arguments(vararg.arg if vararg else None,
                                    kwarg.arg if kwarg else None,
                                    parent)
        else:
            newnode = new.Arguments(vararg, kwarg, parent)
        args = [self.visit(child, newnode, "Assign") for child in node.args]
        defaults = [self.visit(child, newnode, assign_ctx)
                    for child in node.defaults]
        varargannotation = None
        kwargannotation = None
        # change added in 82732 (7c5c678e4164), vararg and kwarg
        # are instances of `_ast.arg`, not strings
        if vararg:
            if PY34:
                vararg = vararg.arg
                if node.vararg.annotation:
                    varargannotation = self.visit(node.vararg.annotation,
                                                  newnode, assign_ctx)
                elif PY3 and node.vararg.annotation:
                    varargannotation = self.visit(node.varargannotation,
                                                  newnode, assign_ctx)
        if kwarg:
            if PY34:
                kwarg = kwarg.arg
                if node.kwarg.annotation:
                    kwargannotation = self.visit(node.kwarg.annotation,
                                                 newnode, assign_ctx)
            elif PY3:
                if node.kwargannotation:
                    kwargannotation = self.visit(node.kwarg.annotation,
                                                 newnode, assign_ctx)
        newnode.postinit(args, defaults,
                         [self.visit(child, newnode, "Assign") for child
                          in node.kwonlyargs] if PY3 else [],
                         [self.visit(child, newnode, None) if child else
                          None for child in node.kw_defaults] if PY3 else [],
                         [self.visit(arg.annotation, newnode, None) if
                          arg.annotation else None for arg in node.args]
                         if PY3 else [],
                         varargannotation, kwargannotation)
        # save argument names in locals:
        if vararg:
            newnode.parent.set_local(vararg, newnode)
        if kwarg:
            newnode.parent.set_local(kwarg, newnode)
        return newnode

    def visit_assignattr(self, node, parent, assign_ctx=None):
        """visit a AssignAttr node by returning a fresh instance of it"""
        newnode = new.AssignAttr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.expr, newnode, None))
        self._delayed_assattr.append(newnode)
        return newnode

    def visit_assert(self, node, parent, assign_ctx=None):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = new.Assert(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         None if node.msg is None else
                         self.visit(node.msg, newnode, assign_ctx))
        return newnode

    def visit_assign(self, node, parent, assign_ctx=None):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = new.Assign(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, "Assign")
                          for child in node.targets],
                         self.visit(node.value, newnode, None))
        klass = newnode.parent.frame()
        if (isinstance(klass, new.ClassDef)
                and isinstance(newnode.value, new.Call)
                and isinstance(newnode.value.func, new.Name)):
            func_name = newnode.value.func.name
            for assign_node in newnode.targets:
                try:
                    meth = klass[assign_node.name]
                    if isinstance(meth, new.FunctionDef):
                        if func_name in ('classmethod', 'staticmethod'):
                            meth.type = func_name
                        elif func_name == 'classproperty': # see lgc.decorators
                            meth.type = 'classmethod'
                        meth.extra_decorators.append(newnode.value)
                except (AttributeError, KeyError):
                    continue
        return newnode

    def visit_assignname(self, node, parent, node_name=None):
        '''visit a node and return a AssignName node'''
        newnode = new.AssignName(node_name, getattr(node, 'lineno', None),
                                 getattr(node, 'col_offset', None), parent)
        self._save_assignment(newnode)
        return newnode

    def visit_augassign(self, node, parent, assign_ctx=None):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = new.AugAssign(_BIN_OP_CLASSES[type(node.op)] + "=",
                                node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.target, newnode, "Assign"),
                         self.visit(node.value, newnode, None))
        return newnode

    def visit_repr(self, node, parent, assign_ctx=None):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = new.Repr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_binop(self, node, parent, assign_ctx=None):
        """visit a BinOp node by returning a fresh instance of it"""
        if isinstance(node.left, BinOp) and self._manager.optimize_ast:
            # Optimize BinOp operations in order to remove
            # redundant recursion. For instance, if the
            # following code is parsed in order to obtain
            # its ast, then the rebuilder will fail with an
            # infinite recursion, the same will happen with the
            # inference engine as well. There's no need to hold
            # so many objects for the BinOp if they can be reduced
            # to something else (also, the optimization
            # might handle only Const binops, which isn't a big
            # problem for the correctness of the program).
            #
            # ("a" + "b" + # one thousand more + "c")
            newnode = self._peepholer.optimize_binop(node, parent)
            if newnode:
                return newnode

        newnode = new.BinOp(_BIN_OP_CLASSES[type(node.op)],
                            node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.left, newnode, assign_ctx),
                         self.visit(node.right, newnode, assign_ctx))
        return newnode

    def visit_boolop(self, node, parent, assign_ctx=None):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = new.BoolOp(_BOOL_OP_CLASSES[type(node.op)],
                             node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.values])
        return newnode

    def visit_break(self, node, parent, assign_ctx=None):
        """visit a Break node by returning a fresh instance of it"""
        return new.Break(getattr(node, 'lineno', None),
                         getattr(node, 'col_offset', None),
                         parent)

    def visit_call(self, node, parent, assign_ctx=None):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = new.Call(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.func, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.args + node.keywords],
                         None if node.starargs is None else
                         self.visit(node.starargs, newnode, assign_ctx),
                         None if node.kwargs is None else
                         self.visit(node.kwargs, newnode, assign_ctx))
        return newnode

    def visit_classdef(self, node, parent, assign_ctx=None, newstyle=None):
        """visit a Class node to become astroid"""
        newnode = new.ClassDef(node.name, None, node.lineno,
                               node.col_offset, parent)
        _init_set_doc(node, newnode)
        metaclass = None
        if PY3:
            for keyword in node.keywords:
                if keyword.arg == 'metaclass':
                    metaclass = self.visit(keyword, newnode, assign_ctx).value
                break
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.bases],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         # py >= 2.6
                         self.visit_decorators(node, newnode, assign_ctx)
                         if 'decorator_list' in node._fields
                         and node.decorator_list else None,
                         newstyle, metaclass)
        return newnode

    def visit_const(self, node, parent, assign_ctx=None):
        """visit a Const node by returning a fresh instance of it"""
        return new.Const(node.value, getattr(node, 'lineno', None),
                         getattr(node, 'col_offset', None), parent)

    def visit_continue(self, node, parent, assign_ctx=None):
        """visit a Continue node by returning a fresh instance of it"""
        return new.Continue(getattr(node, 'lineno', None),
                            getattr(node, 'col_offset', None),
                            parent)

    def visit_compare(self, node, parent, assign_ctx=None):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = new.Compare(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.left, newnode, assign_ctx),
                         [(_CMP_OP_CLASSES[op.__class__],
                           self.visit(expr, newnode, assign_ctx))
                          for (op, expr) in zip(node.ops, node.comparators)])
        return newnode

    def visit_comprehension(self, node, parent, assign_ctx=None):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = new.Comprehension(parent)
        newnode.postinit(self.visit(node.target, newnode, "Assign"),
                         self.visit(node.iter, newnode, None),
                         [self.visit(child, newnode, None)
                          for child in node.ifs])
        return newnode

    def visit_decorators(self, node, parent, assign_ctx=None):
        """visit a Decorators node by returning a fresh instance of it"""
        # /!\ node is actually a _ast.Function node while
        # parent is a astroid.nodes.Function node
        newnode = new.Decorators(node.lineno, node.col_offset, parent)
        if 'decorators' in node._fields: # py < 2.6, i.e. 2.5
            decorators = node.decorators
        else:
            decorators = node.decorator_list
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in decorators])
        return newnode

    def visit_delete(self, node, parent, assign_ctx=None):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = new.Delete(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, "Del")
                          for child in node.targets])
        return newnode

    def visit_dict(self, node, parent, assign_ctx=None):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = new.Dict(node.lineno, node.col_offset, parent)
        newnode.postinit([(self.visit(key, newnode, assign_ctx),
                           self.visit(value, newnode, assign_ctx))
                          for key, value in zip(node.keys, node.values)])
        return newnode

    def visit_dictcomp(self, node, parent, assign_ctx=None):
        """visit a DictComp node by returning a fresh instance of it"""
        newnode = new.DictComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.key, newnode, assign_ctx),
                         self.visit(node.value, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_expr(self, node, parent, assign_ctx=None):
        """visit a Expr node by returning a fresh instance of it"""
        newnode = new.Expr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_ellipsis(self, node, parent, assign_ctx=None):
        """visit an Ellipsis node by returning a fresh instance of it"""
        return new.Ellipsis(getattr(node, 'lineno', None),
                            getattr(node, 'col_offset', None), parent)


    def visit_emptynode(self, node, parent, assign_ctx=None):
        """visit an EmptyNode node by returning a fresh instance of it"""
        return new.EmptyNode(getattr(node, 'lineno', None),
                             getattr(node, 'col_offset', None), parent)


    def visit_excepthandler(self, node, parent, assign_ctx=None):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = new.ExceptHandler(node.lineno, node.col_offset, parent)
        newnode.postinit(None if node.type is None else
                         self.visit(node.type, newnode, assign_ctx),
                         # /!\ node.name can be a tuple
                         None if node.name is None else
                         self.visit(node.name, newnode, "Assign"),
                         [self.visit(child, newnode, None)
                          for child in node.body])
        return newnode

    def visit_exec(self, node, parent, assign_ctx=None):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = new.Exec(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.body, newnode, assign_ctx),
                         None if node.globals is None else
                         self.visit(node.globals, newnode, assign_ctx),
                         None if node.locals is None else
                         self.visit(node.locals, newnode, assign_ctx))
        return newnode

    def visit_extslice(self, node, parent, assign_ctx=None):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = new.ExtSlice(parent=parent)
        newnode.postinit([self.visit(dim, newnode, assign_ctx)
                          for dim in node.dims])
        return newnode

    def visit_for(self, node, parent, assign_ctx=None):
        """visit a For node by returning a fresh instance of it"""
        newnode = new.For(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.target, newnode, "Assign"),
                         self.visit(node.iter, newnode, None),
                         [self.visit(child, newnode, None)
                          for child in node.body],
                         [self.visit(child, newnode, None)
                          for child in node.orelse])
        return newnode

    def visit_importfrom(self, node, parent, assign_ctx=None):
        """visit a From node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = new.ImportFrom(node.module or '', names, node.level or None,
                                 getattr(node, 'lineno', None),
                                 getattr(node, 'col_offset', None), parent)
        # store From names to add them to locals after building
        self._from_nodes.append(newnode)
        return newnode

    def visit_functiondef(self, node, parent, assign_ctx=None):
        """visit an Function node to become astroid"""
        self._global_names.append({})
        newnode = new.FunctionDef(node.name, None, node.lineno,
                                  node.col_offset, parent)
        _init_set_doc(node, newnode)
        if 'decorators' in node._fields: # py < 2.6
            attr = 'decorators'
        else:
            attr = 'decorator_list'
        decorators = getattr(node, attr)
        newnode.postinit(self.visit(node.args, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         self.visit_decorators(node, newnode, assign_ctx)
                         if decorators else None,
                         self.visit(node.returns, newnode, assign_ctx)
                         if PY3 and node.returns else None)
        self._global_names.pop()
        return newnode

    def visit_generatorexp(self, node, parent, assign_ctx=None):
        """visit a GenExpr node by returning a fresh instance of it"""
        newnode = new.GeneratorExp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_attribute(self, node, parent, assign_ctx=None):
        """visit an Attribute node by returning a fresh instance of it"""
        if assign_ctx == "Del":
            # FIXME : maybe we should reintroduce and visit_delattr ?
            # for instance, deactivating assign_ctx
            newnode = new.DelAttr(node.attr, node.lineno, node.col_offset,
                                  parent)
        elif assign_ctx == "Assign":
            # FIXME : maybe we should call visit_assignattr ?
            newnode = new.AssignAttr(node.attr, node.lineno, node.col_offset,
                                     parent)
            self._delayed_assattr.append(newnode)
        else:
            newnode = new.Attribute(node.attr, node.lineno, node.col_offset,
                                    parent)
        newnode.postinit(self.visit(node.value, newnode, None))
        return newnode

    def visit_global(self, node, parent, assign_ctx=None):
        """visit a Global node to become astroid"""
        newnode = new.Global(node.names, getattr(node, 'lineno', None),
                             getattr(node, 'col_offset', None), parent)
        if self._global_names: # global at the module level, no effect
            for name in node.names:
                self._global_names[-1].setdefault(name, []).append(newnode)
        return newnode

    def visit_if(self, node, parent, assign_ctx=None):
        """visit an If node by returning a fresh instance of it"""
        newnode = new.If(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.orelse])
        return newnode

    def visit_ifexp(self, node, parent, assign_ctx=None):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = new.IfExp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         self.visit(node.body, newnode, assign_ctx),
                         self.visit(node.orelse, newnode, assign_ctx))
        return newnode

    def visit_import(self, node, parent, assign_ctx=None):
        """visit a Import node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        # print(names)
        newnode = new.Import(names, getattr(node, 'lineno', None),
                             getattr(node, 'col_offset', None), parent)
        # print(as_string.dump(newnode))
        # print(newnode.names)
        # save import names in parent's locals:
        for (name, asname) in newnode.names:
            name = asname or name
            parent.set_local(name.split('.')[0], newnode)
        return newnode

    def visit_index(self, node, parent, assign_ctx=None):
        """visit a Index node by returning a fresh instance of it"""
        newnode = new.Index(parent=parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_keyword(self, node, parent, assign_ctx=None):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = new.Keyword(node.arg, parent=parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_lambda(self, node, parent, assign_ctx=None):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = new.Lambda(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.args, newnode, assign_ctx),
                         self.visit(node.body, newnode, assign_ctx))
        return newnode

    def visit_list(self, node, parent, assign_ctx=None):
        """visit a List node by returning a fresh instance of it"""
        newnode = new.List(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.elts])
        return newnode

    def visit_listcomp(self, node, parent, assign_ctx=None):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = new.ListComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_name(self, node, parent, assign_ctx=None):
        """visit a Name node by returning a fresh instance of it"""
        # True and False can be assigned to something in py2x, so we have to
        # check first the assign_ctx
        if assign_ctx == "Del":
            newnode = new.DelName(node.id, node.lineno, node.col_offset, parent)
        elif assign_ctx is not None: # Ass
            assert assign_ctx == "Assign"
            newnode = new.AssignName(node.id, node.lineno, node.col_offset,
                                     parent)
        elif node.id in CONST_NAME_TRANSFORMS:
            newnode = new.Const(CONST_NAME_TRANSFORMS[node.id],
                                getattr(node, 'lineno', None),
                                getattr(node, 'col_offset', None), parent)
            return newnode
        else:
            newnode = new.Name(node.id, node.lineno, node.col_offset, parent)
        # XXX REMOVE me :
        if assign_ctx in ('Del', 'Assign'): # 'Aug' ??
            self._save_assignment(newnode)
        return newnode

    def visit_str(self, node, parent, assign_ctx=None):
        """visit a String/Bytes node by returning a fresh instance of Const"""
        return new.Const(node.s, getattr(node, 'lineno', None),
                         getattr(node, 'col_offset', None), parent)
    visit_bytes = visit_str

    def visit_num(self, node, parent, assign_ctx=None):
        """visit a Num node by returning a fresh instance of Const"""
        return new.Const(node.n, getattr(node, 'lineno', None),
                         getattr(node, 'col_offset', None), parent)

    def visit_pass(self, node, parent, assign_ctx=None):
        """visit a Pass node by returning a fresh instance of it"""
        return new.Pass(node.lineno, node.col_offset, parent)

    def visit_print(self, node, parent, assign_ctx=None):
        """visit a Print node by returning a fresh instance of it"""
        newnode = new.Print(node.nl, node.lineno, node.col_offset, parent)
        newnode.postinit(None if node.dest is None else
                         self.visit(node.dest, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.values])
        return newnode

    def visit_raise(self, node, parent, assign_ctx=None):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise(node.lineno, node.col_offset, parent)
        newnode.postinit(None if node.type is None else
                         self.visit(node.type, newnode, assign_ctx),
                         None if node.inst is None else
                         self.visit(node.inst, newnode, assign_ctx),
                         None if node.tback is None else
                         self.visit(node.tback, newnode, assign_ctx))
        return newnode

    def visit_return(self, node, parent, assign_ctx=None):
        """visit a Return node by returning a fresh instance of it"""
        newnode = new.Return(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_set(self, node, parent, assign_ctx=None):
        """visit a Set node by returning a fresh instance of it"""
        newnode = new.Set(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.elts])
        return newnode

    def visit_setcomp(self, node, parent, assign_ctx=None):
        """visit a SetComp node by returning a fresh instance of it"""
        newnode = new.SetComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_slice(self, node, parent, assign_ctx=None):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = new.Slice(parent=parent)
        newnode.postinit(None if node.lower is None else
                         self.visit(node.lower, newnode, assign_ctx),
                         None if node.upper is None else
                         self.visit(node.upper, newnode, assign_ctx),
                         None if node.step is None else
                         self.visit(node.step, newnode, assign_ctx))
        return newnode

    def visit_subscript(self, node, parent, assign_ctx=None):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = new.Subscript(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, None),
                         self.visit(node.slice, newnode, None))
        return newnode

    def visit_tryexcept(self, node, parent, assign_ctx=None):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = new.TryExcept(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.handlers],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.orelse])
        return newnode

    def visit_tryfinally(self, node, parent, assign_ctx=None):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = new.TryFinally(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(n, newnode, assign_ctx)
                          for n in node.finalbody])
        return newnode

    def visit_tuple(self, node, parent, assign_ctx=None):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = new.Tuple(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.elts])
        return newnode

    def visit_unaryop(self, node, parent, assign_ctx=None):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = new.UnaryOp(_UNARY_OP_CLASSES[node.op.__class__],
                              node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.operand, newnode, assign_ctx))
        return newnode

    def visit_while(self, node, parent, assign_ctx=None):
        """visit a While node by returning a fresh instance of it"""
        newnode = new.While(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.orelse])
        return newnode

    def visit_with(self, node, parent, assign_ctx=None):
        newnode = new.With(node.lineno, node.col_offset, parent)
        expr = self.visit(node.context_expr, newnode, assign_ctx)
        if node.optional_vars is not None:
            optional_vars = self.visit(node.optional_vars, newnode, "Assign")
        else:
            optional_vars = None
        newnode.postinit([(expr, optional_vars)],
                         [self.visit(child, newnode, None)
                          for child in node.body])
        return newnode

    def visit_yield(self, node, parent, assign_ctx=None):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = new.Yield(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode


class TreeRebuilder3(TreeRebuilder):
    """extend and overwrite TreeRebuilder for python3k"""

    def visit_arg(self, node, parent, assign_ctx=None):
        """visit a arg node by returning a fresh AssName instance"""
        # TODO(cpopa): introduce an Arg node instead of using AssName.
        return self.visit_assignname(node, parent, node.arg)

    def visit_nameconstant(self, node, parent, assign_ctx=None):
        # in Python 3.4 we have NameConstant for True / False / None
        return new.Const(node.value, getattr(node, 'lineno', None),
                         getattr(node, 'col_offset', None), parent)

    # def visit_arguments(self, node, parent, assign_ctx=None):
    #     return super(TreeRebuilder3, self).visit_arguments(
    #         node, parent, assign_ctx, kwonlyargs, kw_defaults,
    #         annotations)

    def visit_excepthandler(self, node, parent, assign_ctx=None):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = new.ExceptHandler(node.lineno, node.col_offset, parent)
        newnode.postinit(None if node.type is None else
                         self.visit(node.type, newnode, assign_ctx),
                         None if node.name is None else
                         self.visit_assignname(node, newnode, node.name),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body])
        return newnode

    def visit_nonlocal(self, node, parent, assign_ctx=None):
        """visit a Nonlocal node and return a new instance of it"""
        return new.Nonlocal(node.names, getattr(node, 'lineno', None),
                            getattr(node, 'col_offset', None), parent)


    def visit_raise(self, node, parent, assign_ctx=None):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = new.Raise(node.lineno, node.col_offset, parent)
        # no traceback; anyway it is not used in Pylint
        newnode.postinit(None if node.exc is None else
                         self.visit(node.exc, newnode, assign_ctx),
                         None if node.cause is None else
                         self.visit(node.cause, newnode, assign_ctx))
        return newnode

    def visit_starred(self, node, parent, assign_ctx=None):
        """visit a Starred node and return a new instance of it"""
        newnode = new.Starred(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_try(self, node, parent, assign_ctx=None):
        # python 3.3 introduce a new Try node replacing
        # TryFinally/TryExcept nodes
        if node.finalbody:
            newnode = new.TryFinally(node.lineno, node.col_offset, parent)
            newnode.postinit([self.visit_tryexcept(node, newnode, assign_ctx)]
                             if node.handlers else
                             [self.visit(child, newnode, assign_ctx)
                              for child in node.body],
                             [self.visit(n, newnode, assign_ctx)
                              for n in node.finalbody])
            return newnode
        elif node.handlers:
            return self.visit_tryexcept(node, parent, assign_ctx)

    def visit_with(self, node, parent, assign_ctx=None):
        if 'items' not in node._fields:
            # python < 3.3
            return super(TreeRebuilder3, self).visit_with(node, parent,
                                                          assign_ctx)

        newnode = new.With(node.lineno, node.col_offset, parent)
        def visit_child(child):
            expr = self.visit(child.context_expr, newnode, assign_ctx)
            if child.optional_vars:
                var = self.visit(child.optional_vars, newnode, 'Assign')
            else:
                var = None
            return expr, var
        newnode.postinit([visit_child(child) for child in node.items],
                         [self.visit(child, newnode, None)
                          for child in node.body])
        return newnode

    def visit_yieldfrom(self, node, parent, assign_ctx=None):
        newnode = new.YieldFrom(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_classdef(self, node, parent, assign_ctx=None):
        return super(TreeRebuilder3, self).visit_classdef(node, parent,
                                                          assign_ctx,
                                                          True)

if sys.version_info >= (3, 0):
    TreeRebuilder = TreeRebuilder3
