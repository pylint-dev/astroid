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
"""this module contains utilities for rebuilding a ast tree in
order to get a single Astroid representation
"""

import ast
import sys

from astroid import astpeephole
from astroid import nodes


_BIN_OP_CLASSES = {ast.Add: '+',
                   ast.BitAnd: '&',
                   ast.BitOr: '|',
                   ast.BitXor: '^',
                   ast.Div: '/',
                   ast.FloorDiv: '//',
                   ast.Mod: '%',
                   ast.Mult: '*',
                   ast.Pow: '**',
                   ast.Sub: '-',
                   ast.LShift: '<<',
                   ast.RShift: '>>',
                  }
if sys.version_info >= (3, 5):
    _BIN_OP_CLASSES[ast.MatMult] = '@'

_BOOL_OP_CLASSES = {ast.And: 'and',
                    ast.Or: 'or',
                   }

_UNARY_OP_CLASSES = {ast.UAdd: '+',
                     ast.USub: '-',
                     ast.Not: 'not',
                     ast.Invert: '~',
                    }

_CMP_OP_CLASSES = {ast.Eq: '==',
                   ast.Gt: '>',
                   ast.GtE: '>=',
                   ast.In: 'in',
                   ast.Is: 'is',
                   ast.IsNot: 'is not',
                   ast.Lt: '<',
                   ast.LtE: '<=',
                   ast.NotEq: '!=',
                   ast.NotIn: 'not in',
                  }

# Ellipsis is also one of these but has its own node
BUILTIN_NAMES = {'None': None,
                 'NotImplemented': NotImplemented,
                 'True': True,
                 'False': False}

REDIRECT = {'arguments': 'Arguments',
            'comprehension': 'Comprehension',
            "ListCompFor": 'Comprehension',
            "GenExprFor": 'Comprehension',
            'excepthandler': 'ExceptHandler',
            'keyword': 'Keyword',
           }
PY3 = sys.version_info >= (3, 0)
PY34 = sys.version_info >= (3, 4)

def _get_doc(node):
    try:
        if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
            doc = node.body[0].value.s
            node.body = node.body[1:]
            return node, doc
        else:
            return node, None
    except IndexError:
        return node, None


def _visit_or_none(node, attr, visitor, parent, assign_ctx, visit='visit',
                   **kws):
    """If the given node has an attribute, visits the attribute, and
    otherwise returns None.

    """
    value = getattr(node, attr, None)
    if value:
        return getattr(visitor, visit)(value, parent, assign_ctx, **kws)
    else:
        return None


class TreeRebuilder(object):
    """Rebuilds the ast tree to become an Astroid tree"""

    def __init__(self, manager):
        self._manager = manager
        self._global_names = []
        self._visit_meths = {}
        self._peepholer = astpeephole.ASTPeepholeOptimizer()

    def visit_module(self, node, modname, modpath, package):
        """visit a Module node by returning a fresh instance of it"""
        node, doc = _get_doc(node)
        newnode = nodes.Module(name=modname, doc=doc, package=package,
                               pure_python=True, source_file=modpath)
        newnode.postinit([self.visit(child, newnode) for child in node.body])
        return newnode

    def visit(self, node, parent, assign_ctx=None):
        cls = node.__class__
        if cls in self._visit_meths:
            visit_method = self._visit_meths[cls]
        else:
            cls_name = cls.__name__
            visit_name = 'visit_' + REDIRECT.get(cls_name, cls_name).lower()
            visit_method = getattr(self, visit_name)
            self._visit_meths[cls] = visit_method
        return visit_method(node, parent, assign_ctx)

    def visit_arguments(self, node, parent, assign_ctx=None):
        """visit a Arguments node by returning a fresh instance of it"""
        vararg, kwarg = node.vararg, node.kwarg
        if PY34:
            newnode = nodes.Arguments(vararg.arg if vararg else None,
                                      kwarg.arg if kwarg else None,
                                      parent)
        else:
            newnode = nodes.Arguments(vararg, kwarg, parent)
        args = [self.visit(child, newnode, "Assign") for child in node.args]
        defaults = [self.visit(child, newnode, assign_ctx)
                    for child in node.defaults]
        varargannotation = None
        kwargannotation = None
        # change added in 82732 (7c5c678e4164), vararg and kwarg
        # are instances of `ast.arg`, not strings
        if vararg:
            if PY34:
                if node.vararg.annotation:
                    varargannotation = self.visit(node.vararg.annotation,
                                                  newnode, assign_ctx)
                vararg = vararg.arg
            elif PY3 and node.varargannotation:
                varargannotation = self.visit(node.varargannotation,
                                              newnode, assign_ctx)
        if kwarg:
            if PY34:
                if node.kwarg.annotation:
                    kwargannotation = self.visit(node.kwarg.annotation,
                                                 newnode, assign_ctx)
                kwarg = kwarg.arg
            elif PY3:
                if node.kwargannotation:
                    kwargannotation = self.visit(node.kwargannotation,
                                                 newnode, assign_ctx)
        if PY3:
            kwonlyargs = [self.visit(child, newnode, "Assign") for child
                          in node.kwonlyargs]
            kw_defaults = [self.visit(child, newnode, None) if child else
                           None for child in node.kw_defaults]
            annotations = [self.visit(arg.annotation, newnode, None) if
                           arg.annotation else None for arg in node.args]
            kwonly_annotations = [self.visit(arg.annotation, newnode, None)
                                  if arg.annotation else None
                                  for arg in node.kwonlyargs]
        else:
            kwonlyargs = []
            kw_defaults = []
            annotations = []
            kwonly_annotations = []
        newnode.postinit(args, defaults, kwonlyargs, kw_defaults,
                         annotations, kwonly_annotations,
                         varargannotation, kwargannotation)
        return newnode

    def visit_assignattr(self, node, parent, assign_ctx=None):
        """visit a AssignAttr node by returning a fresh instance of it"""
        newnode = nodes.AssignAttr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.expr, newnode, None))
        self._delayed_assattr.append(newnode)
        return newnode

    def visit_assert(self, node, parent, assign_ctx=None):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = nodes.Assert(node.lineno, node.col_offset, parent)
        if node.msg:
            msg = self.visit(node.msg, newnode, assign_ctx)
        else:
            msg = None
        newnode.postinit(self.visit(node.test, newnode, assign_ctx), msg)
        return newnode

    def visit_assign(self, node, parent, assign_ctx=None):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = nodes.Assign(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, "Assign")
                          for child in node.targets],
                         self.visit(node.value, newnode, None))
        return newnode

    def visit_assignname(self, node, parent, assign_ctx=None, node_name=None):
        '''visit a node and return a AssignName node'''
        # assign_ctx is not used here, it takes that argument only to
        # maintain consistency with the other visit functions.
        newnode = nodes.AssignName(node_name, getattr(node, 'lineno', None),
                                   getattr(node, 'col_offset', None), parent)
        return newnode

    def visit_augassign(self, node, parent, assign_ctx=None):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = nodes.AugAssign(_BIN_OP_CLASSES[type(node.op)] + "=",
                                  node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.target, newnode, "Assign"),
                         self.visit(node.value, newnode, None))
        return newnode

    def visit_repr(self, node, parent, assign_ctx=None):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = nodes.Repr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_binop(self, node, parent, assign_ctx=None):
        """visit a BinOp node by returning a fresh instance of it"""
        if isinstance(node.left, ast.BinOp) and self._manager.optimize_ast:
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

        newnode = nodes.BinOp(_BIN_OP_CLASSES[type(node.op)],
                              node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.left, newnode, assign_ctx),
                         self.visit(node.right, newnode, assign_ctx))
        return newnode

    def visit_boolop(self, node, parent, assign_ctx=None):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = nodes.BoolOp(_BOOL_OP_CLASSES[type(node.op)],
                               node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.values])
        return newnode

    def visit_break(self, node, parent, assign_ctx=None):
        """visit a Break node by returning a fresh instance of it"""
        return nodes.Break(getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None),
                           parent)

    def visit_call(self, node, parent, assign_ctx=None):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = nodes.Call(node.lineno, node.col_offset, parent)
        starargs = _visit_or_none(node, 'starargs', self, newnode,
                                  assign_ctx)
        kwargs = _visit_or_none(node, 'kwargs', self, newnode,
                                assign_ctx)
        args = [self.visit(child, newnode, assign_ctx)
                for child in node.args]

        if node.keywords:
            keywords = [self.visit(child, newnode, assign_ctx)
                        for child in node.keywords]
        else:
            keywords = None
        if starargs:
            new_starargs = nodes.Starred(col_offset=starargs.col_offset,
                                         lineno=starargs.lineno,
                                         parent=starargs.parent)
            new_starargs.postinit(value=starargs)
            args.append(new_starargs)
        if kwargs:
            new_kwargs = nodes.Keyword(arg=None, col_offset=kwargs.col_offset,
                                       lineno=kwargs.lineno,
                                       parent=kwargs.parent)
            new_kwargs.postinit(value=kwargs)
            if keywords:
                keywords.append(new_kwargs)
            else:
                keywords = [new_kwargs]
        newnode.postinit(self.visit(node.func, newnode, assign_ctx),
                         args, keywords)
        return newnode

    def visit_classdef(self, node, parent, assign_ctx=None, newstyle=None):
        """visit a ClassDef node to become astroid"""
        node, doc = _get_doc(node)
        newnode = nodes.ClassDef(node.name, doc, node.lineno,
                                 node.col_offset, parent)
        metaclass = None
        if PY3:
            for keyword in node.keywords:
                if keyword.arg == 'metaclass':
                    metaclass = self.visit(keyword, newnode, assign_ctx).value
                break
        if node.decorator_list:
            decorators = self.visit_decorators(node, newnode, assign_ctx)
        else:
            decorators = None
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.bases],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         decorators, newstyle, metaclass)
        return newnode

    def visit_const(self, node, parent, assign_ctx=None):
        """visit a Const node by returning a fresh instance of it"""
        return nodes.Const(node.value, getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None), parent)

    def visit_continue(self, node, parent, assign_ctx=None):
        """visit a Continue node by returning a fresh instance of it"""
        return nodes.Continue(getattr(node, 'lineno', None),
                              getattr(node, 'col_offset', None),
                              parent)

    def visit_compare(self, node, parent, assign_ctx=None):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = nodes.Compare(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.left, newnode, assign_ctx),
                         [(_CMP_OP_CLASSES[op.__class__],
                           self.visit(expr, newnode, assign_ctx))
                          for (op, expr) in zip(node.ops, node.comparators)])
        return newnode

    def visit_comprehension(self, node, parent, assign_ctx=None):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = nodes.Comprehension(parent)
        newnode.postinit(self.visit(node.target, newnode, "Assign"),
                         self.visit(node.iter, newnode, None),
                         [self.visit(child, newnode, None)
                          for child in node.ifs])
        return newnode

    def visit_decorators(self, node, parent, assign_ctx=None):
        """visit a Decorators node by returning a fresh instance of it"""
        # /!\ node is actually a ast.FunctionDef node while
        # parent is a astroid.nodes.FunctionDef node
        newnode = nodes.Decorators(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.decorator_list])
        return newnode

    def visit_delete(self, node, parent, assign_ctx=None):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = nodes.Delete(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, "Del")
                          for child in node.targets])
        return newnode

    def _visit_dict_items(self, node, parent, newnode, assign_ctx):
        for key, value in zip(node.keys, node.values):
            rebuilt_value = self.visit(value, newnode, assign_ctx)
            if not key:
                # Python 3.5 and extended unpacking
                rebuilt_key = nodes.DictUnpack(rebuilt_value.lineno,
                                               rebuilt_value.col_offset,
                                               parent)
            else:
                rebuilt_key = self.visit(key, newnode, assign_ctx)
            yield rebuilt_key, rebuilt_value

    def visit_dict(self, node, parent, assign_ctx=None):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = nodes.Dict(node.lineno, node.col_offset, parent)
        items = list(self._visit_dict_items(node, parent, newnode, assign_ctx))
        newnode.postinit(items)
        return newnode

    def visit_dictcomp(self, node, parent, assign_ctx=None):
        """visit a DictComp node by returning a fresh instance of it"""
        newnode = nodes.DictComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.key, newnode, assign_ctx),
                         self.visit(node.value, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_expr(self, node, parent, assign_ctx=None):
        """visit a Expr node by returning a fresh instance of it"""
        newnode = nodes.Expr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_ellipsis(self, node, parent, assign_ctx=None):
        """visit an Ellipsis node by returning a fresh instance of it"""
        return nodes.Ellipsis(getattr(node, 'lineno', None),
                              getattr(node, 'col_offset', None), parent)

    def visit_excepthandler(self, node, parent, assign_ctx=None):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = nodes.ExceptHandler(node.lineno, node.col_offset, parent)
        # /!\ node.name can be a tuple
        newnode.postinit(_visit_or_none(node, 'type', self, newnode, assign_ctx),
                         _visit_or_none(node, 'name', self, newnode, 'Assign'),
                         [self.visit(child, newnode, None)
                          for child in node.body])
        return newnode

    def visit_exec(self, node, parent, assign_ctx=None):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = nodes.Exec(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.body, newnode, assign_ctx),
                         _visit_or_none(node, 'globals', self, newnode,
                                        assign_ctx),
                         _visit_or_none(node, 'locals', self, newnode,
                                        assign_ctx))
        return newnode

    def visit_extslice(self, node, parent, assign_ctx=None):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = nodes.ExtSlice(parent=parent)
        newnode.postinit([self.visit(dim, newnode, assign_ctx)
                          for dim in node.dims])
        return newnode

    def _visit_for(self, cls, node, parent, assign_ctx=None):
        """visit a For node by returning a fresh instance of it"""
        newnode = cls(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.target, newnode, "Assign"),
                         self.visit(node.iter, newnode, None),
                         [self.visit(child, newnode, None)
                          for child in node.body],
                         [self.visit(child, newnode, None)
                          for child in node.orelse])
        return newnode

    def visit_for(self, node, parent, assign_ctx=None):
        return self._visit_for(nodes.For, node, parent,
                               assign_ctx=assign_ctx)

    def visit_importfrom(self, node, parent, assign_ctx=None):
        """visit an ImportFrom node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = nodes.ImportFrom(node.module or '', names, node.level or None,
                                   getattr(node, 'lineno', None),
                                   getattr(node, 'col_offset', None), parent)
        return newnode

    def _visit_functiondef(self, cls, node, parent, assign_ctx=None):
        """visit an FunctionDef node to become astroid"""
        self._global_names.append({})
        node, doc = _get_doc(node)
        newnode = cls(node.name, doc, node.lineno,
                      node.col_offset, parent)
        if node.decorator_list:
            decorators = self.visit_decorators(node, newnode, assign_ctx)
        else:
            decorators = None
        if PY3 and node.returns:
            returns = self.visit(node.returns, newnode, assign_ctx)
        else:
            returns = None
        newnode.postinit(self.visit(node.args, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         decorators, returns)
        self._global_names.pop()
        return newnode

    def visit_functiondef(self, node, parent, assign_ctx=None):
        return self._visit_functiondef(nodes.FunctionDef, node, parent,
                                       assign_ctx=assign_ctx)

    def visit_generatorexp(self, node, parent, assign_ctx=None):
        """visit a GeneratorExp node by returning a fresh instance of it"""
        newnode = nodes.GeneratorExp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_attribute(self, node, parent, assign_ctx=None):
        """visit an Attribute node by returning a fresh instance of it"""
        if assign_ctx == "Del":
            # FIXME : maybe we should reintroduce and visit_delattr ?
            # for instance, deactivating assign_ctx
            newnode = nodes.DelAttr(node.attr, node.lineno, node.col_offset,
                                    parent)
        elif assign_ctx == "Assign":
            # FIXME : maybe we should call visit_assignattr ?
            newnode = nodes.AssignAttr(node.attr, node.lineno, node.col_offset,
                                       parent)
        else:
            newnode = nodes.Attribute(node.attr, node.lineno, node.col_offset,
                                      parent)
        newnode.postinit(self.visit(node.value, newnode, None))
        return newnode

    def visit_global(self, node, parent, assign_ctx=None):
        """visit a Global node to become astroid"""
        newnode = nodes.Global(node.names, getattr(node, 'lineno', None),
                               getattr(node, 'col_offset', None), parent)
        if self._global_names: # global at the module level, no effect
            for name in node.names:
                self._global_names[-1].setdefault(name, []).append(newnode)
        return newnode

    def visit_if(self, node, parent, assign_ctx=None):
        """visit an If node by returning a fresh instance of it"""
        newnode = nodes.If(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.orelse])
        return newnode

    def visit_ifexp(self, node, parent, assign_ctx=None):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = nodes.IfExp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         self.visit(node.body, newnode, assign_ctx),
                         self.visit(node.orelse, newnode, assign_ctx))
        return newnode

    def visit_import(self, node, parent, assign_ctx=None):
        """visit a Import node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = nodes.Import(names, getattr(node, 'lineno', None),
                               getattr(node, 'col_offset', None), parent)
        return newnode

    def visit_index(self, node, parent, assign_ctx=None):
        """visit a Index node by returning a fresh instance of it"""
        newnode = nodes.Index(parent=parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_keyword(self, node, parent, assign_ctx=None):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = nodes.Keyword(node.arg, parent=parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_lambda(self, node, parent, assign_ctx=None):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = nodes.Lambda(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.args, newnode, assign_ctx),
                         self.visit(node.body, newnode, assign_ctx))
        return newnode

    def visit_list(self, node, parent, assign_ctx=None):
        """visit a List node by returning a fresh instance of it"""
        newnode = nodes.List(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.elts])
        return newnode

    def visit_listcomp(self, node, parent, assign_ctx=None):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = nodes.ListComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_name(self, node, parent, assign_ctx=None):
        """visit a Name node by returning a fresh instance of it"""
        # True and False can be assigned to something in py2x, so we have to
        # check first the assign_ctx
        if assign_ctx == "Del":
            newnode = nodes.DelName(node.id, node.lineno, node.col_offset,
                                    parent)
        elif assign_ctx is not None: # Assign
            assert assign_ctx == "Assign"
            newnode = nodes.AssignName(node.id, node.lineno, node.col_offset,
                                       parent)
        elif node.id in BUILTIN_NAMES:
            newnode = nodes.NameConstant(BUILTIN_NAMES[node.id],
                                         getattr(node, 'lineno', None),
                                         getattr(node, 'col_offset', None),
                                         parent)
            return newnode
        else:
            newnode = nodes.Name(node.id, node.lineno, node.col_offset, parent)
        return newnode

    def visit_str(self, node, parent, assign_ctx=None):
        """visit a String/Bytes node by returning a fresh instance of Const"""
        return nodes.Const(node.s, getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None), parent)
    visit_bytes = visit_str

    def visit_num(self, node, parent, assign_ctx=None):
        """visit a Num node by returning a fresh instance of Const"""
        return nodes.Const(node.n, getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None), parent)

    def visit_pass(self, node, parent, assign_ctx=None):
        """visit a Pass node by returning a fresh instance of it"""
        return nodes.Pass(node.lineno, node.col_offset, parent)

    def visit_print(self, node, parent, assign_ctx=None):
        """visit a Print node by returning a fresh instance of it"""
        newnode = nodes.Print(node.nl, node.lineno, node.col_offset, parent)
        newnode.postinit(_visit_or_none(node, 'dest', self, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.values])
        return newnode

    def visit_raise(self, node, parent, assign_ctx=None):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = nodes.Raise(node.lineno, node.col_offset, parent)
        newnode.postinit(_visit_or_none(node, 'type', self, newnode, assign_ctx),
                         _visit_or_none(node, 'inst', self, newnode, assign_ctx),
                         _visit_or_none(node, 'tback', self, newnode,
                                        assign_ctx))
        return newnode

    def visit_return(self, node, parent, assign_ctx=None):
        """visit a Return node by returning a fresh instance of it"""
        newnode = nodes.Return(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_set(self, node, parent, assign_ctx=None):
        """visit a Set node by returning a fresh instance of it"""
        newnode = nodes.Set(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.elts])
        return newnode

    def visit_setcomp(self, node, parent, assign_ctx=None):
        """visit a SetComp node by returning a fresh instance of it"""
        newnode = nodes.SetComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.generators])
        return newnode

    def visit_slice(self, node, parent, assign_ctx=None):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = nodes.Slice(parent=parent)
        newnode.postinit(_visit_or_none(node, 'lower', self, newnode,
                                        assign_ctx),
                         _visit_or_none(node, 'upper', self, newnode,
                                        assign_ctx),
                         _visit_or_none(node, 'step', self, newnode, assign_ctx))
        return newnode

    def visit_subscript(self, node, parent, assign_ctx=None):
        """visit a Subscript node by returning a fresh instance of it"""
        newnode = nodes.Subscript(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, None),
                         self.visit(node.slice, newnode, None))
        return newnode

    def visit_tryexcept(self, node, parent, assign_ctx=None):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = nodes.TryExcept(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.handlers],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.orelse])
        return newnode

    def visit_tryfinally(self, node, parent, assign_ctx=None):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = nodes.TryFinally(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(n, newnode, assign_ctx)
                          for n in node.finalbody])
        return newnode

    def visit_tuple(self, node, parent, assign_ctx=None):
        """visit a Tuple node by returning a fresh instance of it"""
        newnode = nodes.Tuple(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode, assign_ctx)
                          for child in node.elts])
        return newnode

    def visit_unaryop(self, node, parent, assign_ctx=None):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = nodes.UnaryOp(_UNARY_OP_CLASSES[node.op.__class__],
                                node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.operand, newnode, assign_ctx))
        return newnode

    def visit_while(self, node, parent, assign_ctx=None):
        """visit a While node by returning a fresh instance of it"""
        newnode = nodes.While(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode, assign_ctx),
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body],
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.orelse])
        return newnode

    def visit_with(self, node, parent, assign_ctx=None):
        newnode = nodes.With(node.lineno, node.col_offset, parent)
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
        newnode = nodes.Yield(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode


class TreeRebuilder3(TreeRebuilder):
    """extend and overwrite TreeRebuilder for python3k"""

    def visit_arg(self, node, parent, assign_ctx=None):
        """visit a arg node by returning a fresh AssName instance"""
        # TODO(cpopa): introduce an Arg node instead of using AssignName.
        return self.visit_assignname(node, parent, assign_ctx, node.arg)

    def visit_nameconstant(self, node, parent, assign_ctx=None):
        # in Python 3.4 we have NameConstant for True / False / None
        return nodes.NameConstant(node.value, getattr(node, 'lineno', None),
                                  getattr(node, 'col_offset', None), parent)

    def visit_excepthandler(self, node, parent, assign_ctx=None):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = nodes.ExceptHandler(node.lineno, node.col_offset, parent)
        if node.name:
            name = self.visit_assignname(node, newnode, assign_ctx, node.name)
        else:
            name = None
        newnode.postinit(_visit_or_none(node, 'type', self, newnode, assign_ctx),
                         name,
                         [self.visit(child, newnode, assign_ctx)
                          for child in node.body])
        return newnode

    def visit_nonlocal(self, node, parent, assign_ctx=None):
        """visit a Nonlocal node and return a new instance of it"""
        return nodes.Nonlocal(node.names, getattr(node, 'lineno', None),
                              getattr(node, 'col_offset', None), parent)


    def visit_raise(self, node, parent, assign_ctx=None):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = nodes.Raise(node.lineno, node.col_offset, parent)
        # no traceback; anyway it is not used in Pylint
        newnode.postinit(_visit_or_none(node, 'exc', self, newnode, assign_ctx),
                         _visit_or_none(node, 'cause', self, newnode,
                                        assign_ctx))
        return newnode

    def visit_starred(self, node, parent, assign_ctx=None):
        """visit a Starred node and return a new instance of it"""
        newnode = nodes.Starred(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_try(self, node, parent, assign_ctx=None):
        # python 3.3 introduce a new Try node replacing
        # TryFinally/TryExcept nodes
        if node.finalbody:
            newnode = nodes.TryFinally(node.lineno, node.col_offset, parent)
            if node.handlers:
                body = [self.visit_tryexcept(node, newnode, assign_ctx)]
            else:
                body = [self.visit(child, newnode, assign_ctx)
                        for child in node.body]
            newnode.postinit(body,
                             [self.visit(n, newnode, assign_ctx)
                              for n in node.finalbody])
            return newnode
        elif node.handlers:
            return self.visit_tryexcept(node, parent, assign_ctx)

    def _visit_with(self, cls, node, parent, assign_ctx=None):
        if 'items' not in node._fields:
            # python < 3.3
            return super(TreeRebuilder3, self).visit_with(node, parent,
                                                          assign_ctx)

        newnode = cls(node.lineno, node.col_offset, parent)
        def visit_child(child):
            expr = self.visit(child.context_expr, newnode, assign_ctx)
            var = _visit_or_none(child, 'optional_vars', self, newnode,
                                 'Assign')
            return expr, var
        newnode.postinit([visit_child(child) for child in node.items],
                         [self.visit(child, newnode, None)
                          for child in node.body])
        return newnode

    def visit_with(self, node, parent, assign_ctx=None):
        return self._visit_with(nodes.With, node, parent, assign_ctx=assign_ctx)

    def visit_yieldfrom(self, node, parent, assign_ctx=None):
        newnode = nodes.YieldFrom(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode, assign_ctx))
        return newnode

    def visit_classdef(self, node, parent, assign_ctx=None, newstyle=True):
        return super(TreeRebuilder3, self).visit_classdef(node, parent,
                                                          assign_ctx,
                                                          newstyle=newstyle)

    # Async structs added in Python 3.5
    def visit_asyncfunctiondef(self, node, parent, assign_ctx=None):
        return self._visit_functiondef(nodes.AsyncFunctionDef, node, parent,
                                       assign_ctx=assign_ctx)

    def visit_asyncfor(self, node, parent, assign_ctx=None):
        return self._visit_for(nodes.AsyncFor, node, parent,
                               assign_ctx=assign_ctx)

    def visit_await(self, node, parent, assign_ctx=None):
        newnode = nodes.Await(node.lineno, node.col_offset, parent)
        newnode.postinit(value=self.visit(node.value, newnode, None))
        return newnode

    def visit_asyncwith(self, node, parent, assign_ctx=None):
        return self._visit_with(nodes.AsyncWith, node, parent,
                                assign_ctx=assign_ctx)


if sys.version_info >= (3, 0):
    TreeRebuilder = TreeRebuilder3
