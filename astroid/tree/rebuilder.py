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
import collections
import sys

import astroid
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
CONTEXTS = {ast.Load: astroid.Load,
            ast.Store: astroid.Store,
            ast.Del: astroid.Del,
            ast.Param: astroid.Store}


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

def _visit_or_empty(node, attr, visitor, parent, visit='visit', **kws):
    """If the given node has an attribute, visits the attribute, and
    otherwise returns None.

    """
    value = getattr(node, attr, None)
    if value:
        return getattr(visitor, visit)(value, parent, **kws)
    else:
        return nodes.Empty


def _get_context(node):
    return CONTEXTS.get(type(node.ctx), astroid.Load)


class ParameterVisitor(object):
    """A visitor which is used for building the components of Arguments node."""

    def __init__(self, visitor):
        self._visitor = visitor

    def visit(self, param_node, *args):
        cls_name = param_node.__class__.__name__
        visit_name = 'visit_' + REDIRECT.get(cls_name, cls_name).lower()
        visit_method = getattr(self, visit_name)
        return visit_method(param_node, *args) 

    def visit_arg(self, param_node, *args):
        name = param_node.arg
        return self._build_parameter(param_node, name, *args)

    def visit_name(self, param_node, *args):
        name = param_node.id
        return self._build_parameter(param_node, name, *args)

    def visit_tuple(self, param_node, parent, default):
        # We're not supporting nested arguments anymore, but in order to
        # simply not crash when running on Python 2, we're unpacking the elements
        # before hand. We simply don't want to support this feature anymore,
        # so it's possible to be broken.
        converted_node = self._visitor.visit(param_node, parent)
        for element in converted_node.elts:
            param = nodes.Parameter(name=element.name, lineno=param_node.lineno,
                                    col_offset=param_node.col_offset,
                                    parent=parent)
            param.postinit(default=default, annotation=nodes.Empty)
            yield param

    def _build_parameter(self, param_node, name, parent, default):
        param = nodes.Parameter(name=name, lineno=getattr(param_node, 'lineno', None),
                                col_offset=getattr(param_node, 'col_offset', None),
                                parent=parent)
        annotation = nodes.Empty
        param_annotation = getattr(param_node, 'annotation', nodes.Empty)
        if param_annotation:
            annotation = self._visitor.visit(param_annotation, param)

        param.postinit(default=default, annotation=annotation)
        yield param



class TreeRebuilder(object):
    """Rebuilds the ast tree to become an Astroid tree"""

    def __init__(self):
        self._global_names = []
        self._visit_meths = {}

    def visit_module(self, node, modname, modpath, package):
        """visit a Module node by returning a fresh instance of it"""
        node, doc = _get_doc(node)
        newnode = nodes.Module(name=modname, doc=doc, package=package,
                               pure_python=True, source_file=modpath)
        newnode.postinit([self.visit(child, newnode) for child in node.body])
        return newnode

    def visit(self, node, parent):
        cls = node.__class__
        if cls in self._visit_meths:
            visit_method = self._visit_meths[cls]
        else:
            cls_name = cls.__name__
            visit_name = 'visit_' + REDIRECT.get(cls_name, cls_name).lower()
            visit_method = getattr(self, visit_name)
            self._visit_meths[cls] = visit_method
        return visit_method(node, parent)

    def visit_arguments(self, node, parent):
        """visit a Arguments node by returning a fresh instance of it"""
        def _build_variadic(field_name):
            param = nodes.Empty
            variadic = getattr(node, field_name)

            if variadic:
                # Various places to get the name from.
                try:
                    param_name = variadic.id
                except AttributeError:
                    try:
                        param_name = variadic.arg
                    except AttributeError:
                        param_name = variadic

                param = nodes.Parameter(name=param_name,
                                        lineno=newnode.lineno,
                                        col_offset=newnode.col_offset,
                                        parent=newnode)
                # Get the annotation of the variadic node.
                annotation = nodes.Empty
                default = nodes.Empty
                variadic_annotation = getattr(variadic, 'annotation', nodes.Empty)
                if variadic_annotation is None:
                    # Support for Python 3.3.
                    variadic_annotation = getattr(node, field_name + 'annotation', nodes.Empty)
                if variadic_annotation:
                    annotation = self.visit(variadic_annotation, param)

                param.postinit(default=default, annotation=annotation)
            return param

        def _build_args(params, defaults):
            # Pad the list of defaults so that each arguments gets a default.
            defaults = collections.deque(defaults)
            while len(defaults) != len(params):
                defaults.appendleft(nodes.Empty)

            param_visitor = ParameterVisitor(self)
            for parameter in params:
                default = defaults.popleft()
                if default:
                    default = self.visit(default, newnode)

                for param in param_visitor.visit(parameter, newnode, default):
                    yield param

        newnode = nodes.Arguments(parent=parent)
        # Build the arguments list.
        positional_args = list(_build_args(node.args, node.defaults))
        kwonlyargs = list(_build_args(getattr(node, 'kwonlyargs', ()),
                                              getattr(node, 'kw_defaults', ())))
        # Build vararg and kwarg.
        vararg = _build_variadic('vararg')
        kwarg = _build_variadic('kwarg')
        # Prepare the arguments new node.
        newnode.postinit(args=positional_args, vararg=vararg, kwarg=kwarg,
                         keyword_only=kwonlyargs,
                         positional_only=[])
        return newnode

    def visit_assert(self, node, parent):
        """visit a Assert node by returning a fresh instance of it"""
        newnode = nodes.Assert(node.lineno, node.col_offset, parent)
        if node.msg:
            msg = self.visit(node.msg, newnode)
        else:
            msg = nodes.Empty
        newnode.postinit(self.visit(node.test, newnode), msg)
        return newnode

    def visit_assign(self, node, parent):
        """visit a Assign node by returning a fresh instance of it"""
        newnode = nodes.Assign(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.targets],
                         self.visit(node.value, newnode))
        return newnode

    def visit_assignname(self, node, parent, node_name=None):
        '''visit a node and return a AssignName node'''
        newnode = nodes.AssignName(node_name, getattr(node, 'lineno', None),
                                   getattr(node, 'col_offset', None), parent)
        return newnode

    def visit_augassign(self, node, parent):
        """visit a AugAssign node by returning a fresh instance of it"""
        newnode = nodes.AugAssign(_BIN_OP_CLASSES[type(node.op)] + "=",
                                  node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.target, newnode),
                         self.visit(node.value, newnode))
        return newnode

    def visit_repr(self, node, parent):
        """visit a Backquote node by returning a fresh instance of it"""
        newnode = nodes.Repr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_binop(self, node, parent):
        """visit a BinOp node by returning a fresh instance of it"""
        newnode = nodes.BinOp(_BIN_OP_CLASSES[type(node.op)],
                              node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.left, newnode),
                         self.visit(node.right, newnode))
        return newnode

    def visit_boolop(self, node, parent):
        """visit a BoolOp node by returning a fresh instance of it"""
        newnode = nodes.BoolOp(_BOOL_OP_CLASSES[type(node.op)],
                               node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.values])
        return newnode

    def visit_break(self, node, parent):
        """visit a Break node by returning a fresh instance of it"""
        return nodes.Break(getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None),
                           parent)

    def visit_call(self, node, parent):
        """visit a CallFunc node by returning a fresh instance of it"""
        newnode = nodes.Call(node.lineno, node.col_offset, parent)
        starargs = _visit_or_empty(node, 'starargs', self, newnode)
        kwargs = _visit_or_empty(node, 'kwargs', self, newnode)
        args = [self.visit(child, newnode)
                for child in node.args]

        if node.keywords:
            keywords = [self.visit(child, newnode)
                        for child in node.keywords]
        else:
            keywords = ()
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

        newnode.postinit(self.visit(node.func, newnode),
                         args, keywords)
        return newnode

    def visit_classdef(self, node, parent, newstyle=None):
        """visit a ClassDef node to become astroid"""
        node, doc = _get_doc(node)
        newnode = nodes.ClassDef(node.name, doc, node.lineno,
                                 node.col_offset, parent)
        metaclass = None
        if PY3:
            for keyword in node.keywords:
                if keyword.arg == 'metaclass':
                    metaclass = self.visit(keyword, newnode).value
                break
        if node.decorator_list:
            decorators = self.visit_decorators(node, newnode)
        else:
            decorators = nodes.Empty
        newnode.postinit([self.visit(child, newnode)
                          for child in node.bases],
                         [self.visit(child, newnode)
                          for child in node.body],
                         decorators, newstyle, metaclass)
        return newnode

    def visit_const(self, node, parent):
        """visit a Const node by returning a fresh instance of it"""
        return nodes.Const(node.value, getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None), parent)

    def visit_continue(self, node, parent):
        """visit a Continue node by returning a fresh instance of it"""
        return nodes.Continue(getattr(node, 'lineno', None),
                              getattr(node, 'col_offset', None),
                              parent)

    def visit_compare(self, node, parent):
        """visit a Compare node by returning a fresh instance of it"""
        newnode = nodes.Compare([_CMP_OP_CLASSES[type(op)] for op in
                                 node.ops], node.lineno,
                                node.col_offset, parent)
        newnode.postinit(self.visit(node.left, newnode),
                         [self.visit(expr, newnode)
                          for expr in node.comparators])
        return newnode

    def visit_comprehension(self, node, parent):
        """visit a Comprehension node by returning a fresh instance of it"""
        newnode = nodes.Comprehension(parent)
        newnode.postinit(self.visit(node.target, newnode),
                         self.visit(node.iter, newnode),
                         [self.visit(child, newnode)
                          for child in node.ifs])
        return newnode

    def visit_decorators(self, node, parent):
        """visit a Decorators node by returning a fresh instance of it"""
        # /!\ node is actually a ast.FunctionDef node while
        # parent is a astroid.nodes.FunctionDef node
        newnode = nodes.Decorators(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.decorator_list])
        return newnode

    def visit_delete(self, node, parent):
        """visit a Delete node by returning a fresh instance of it"""
        newnode = nodes.Delete(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.targets])
        return newnode

    def _visit_dict_items(self, node, parent, newnode):
        for key, value in zip(node.keys, node.values):
            rebuilt_value = self.visit(value, newnode)
            if not key:
                # Python 3.5 and extended unpacking
                rebuilt_key = nodes.DictUnpack(rebuilt_value.lineno,
                                               rebuilt_value.col_offset,
                                               parent)
            else:
                rebuilt_key = self.visit(key, newnode)
            yield rebuilt_key, rebuilt_value

    def visit_dict(self, node, parent):
        """visit a Dict node by returning a fresh instance of it"""
        newnode = nodes.Dict(node.lineno, node.col_offset, parent)
        items = list(self._visit_dict_items(node, parent, newnode))
        if items:
            keys, values = zip(*items)
        else:
            keys, values = [], []
        newnode.postinit(keys, values)
        return newnode

    def visit_dictcomp(self, node, parent):
        """visit a DictComp node by returning a fresh instance of it"""
        newnode = nodes.DictComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.key, newnode),
                         self.visit(node.value, newnode),
                         [self.visit(child, newnode)
                          for child in node.generators])
        return newnode

    def visit_expr(self, node, parent):
        """visit a Expr node by returning a fresh instance of it"""
        newnode = nodes.Expr(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_ellipsis(self, node, parent):
        """visit an Ellipsis node by returning a fresh instance of it"""
        return nodes.Ellipsis(getattr(node, 'lineno', None),
                              getattr(node, 'col_offset', None), parent)

    def visit_excepthandler(self, node, parent):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = nodes.ExceptHandler(node.lineno, node.col_offset, parent)
        # /!\ node.name can be a tuple
        newnode.postinit(_visit_or_empty(node, 'type', self, newnode),
                         _visit_or_empty(node, 'name', self, newnode),
                         [self.visit(child, newnode)
                          for child in node.body])
        return newnode

    def visit_exec(self, node, parent):
        """visit an Exec node by returning a fresh instance of it"""
        newnode = nodes.Exec(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.body, newnode),
                         _visit_or_empty(node, 'globals', self, newnode),
                         _visit_or_empty(node, 'locals', self, newnode))
        return newnode

    def visit_extslice(self, node, parent):
        """visit an ExtSlice node by returning a fresh instance of it"""
        newnode = nodes.ExtSlice(parent=parent)
        newnode.postinit([self.visit(dim, newnode) for dim in node.dims])
        return newnode

    def _visit_for(self, cls, node, parent):
        """visit a For node by returning a fresh instance of it"""
        newnode = cls(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.target, newnode),
                         self.visit(node.iter, newnode),
                         [self.visit(child, newnode)
                          for child in node.body],
                         [self.visit(child, newnode)
                          for child in node.orelse])
        return newnode

    def visit_for(self, node, parent):
        return self._visit_for(nodes.For, node, parent)

    def visit_importfrom(self, node, parent):
        """visit an ImportFrom node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = nodes.ImportFrom(node.module or '', names, node.level or None,
                                   getattr(node, 'lineno', None),
                                   getattr(node, 'col_offset', None), parent)
        return newnode

    def _visit_functiondef(self, cls, node, parent):
        """visit an FunctionDef node to become astroid"""
        self._global_names.append({})
        node, doc = _get_doc(node)
        newnode = cls(node.name, doc, node.lineno,
                      node.col_offset, parent)
        if node.decorator_list:
            decorators = self.visit_decorators(node, newnode)
        else:
            decorators = nodes.Empty
        if PY3 and node.returns:
            returns = self.visit(node.returns, newnode)
        else:
            returns = nodes.Empty
        newnode.postinit(self.visit(node.args, newnode),
                         [self.visit(child, newnode)
                          for child in node.body],
                         decorators, returns)
        self._global_names.pop()
        return newnode

    def visit_functiondef(self, node, parent):
        return self._visit_functiondef(nodes.FunctionDef, node, parent)

    def visit_generatorexp(self, node, parent):
        """visit a GeneratorExp node by returning a fresh instance of it"""
        newnode = nodes.GeneratorExp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode),
                         [self.visit(child, newnode)
                          for child in node.generators])
        return newnode

    def visit_attribute(self, node, parent):
        """visit an Attribute node by returning a fresh instance of it"""
        context = _get_context(node)
        if context == astroid.Del:
            # FIXME : maybe we should reintroduce and visit_delattr ?
            # for instance, deactivating assign_ctx
            newnode = nodes.DelAttr(node.attr, node.lineno, node.col_offset,
                                    parent)
        elif context == astroid.Store:
            newnode = nodes.AssignAttr(node.attr, node.lineno, node.col_offset,
                                       parent)
        else:
            newnode = nodes.Attribute(node.attr, node.lineno, node.col_offset,
                                      parent)
        newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_global(self, node, parent):
        """visit a Global node to become astroid"""
        newnode = nodes.Global(node.names, getattr(node, 'lineno', None),
                               getattr(node, 'col_offset', None), parent)
        if self._global_names: # global at the module level, no effect
            for name in node.names:
                self._global_names[-1].setdefault(name, []).append(newnode)
        return newnode

    def visit_if(self, node, parent):
        """visit an If node by returning a fresh instance of it"""
        newnode = nodes.If(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode),
                         [self.visit(child, newnode)
                          for child in node.body],
                         [self.visit(child, newnode)
                          for child in node.orelse])
        return newnode

    def visit_ifexp(self, node, parent):
        """visit a IfExp node by returning a fresh instance of it"""
        newnode = nodes.IfExp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode),
                         self.visit(node.body, newnode),
                         self.visit(node.orelse, newnode))
        return newnode

    def visit_import(self, node, parent):
        """visit a Import node by returning a fresh instance of it"""
        names = [(alias.name, alias.asname) for alias in node.names]
        newnode = nodes.Import(names, getattr(node, 'lineno', None),
                               getattr(node, 'col_offset', None), parent)
        return newnode

    def visit_index(self, node, parent):
        """visit a Index node by returning a fresh instance of it"""
        newnode = nodes.Index(parent=parent)
        newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_keyword(self, node, parent):
        """visit a Keyword node by returning a fresh instance of it"""
        newnode = nodes.Keyword(node.arg, parent=parent)
        newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_lambda(self, node, parent):
        """visit a Lambda node by returning a fresh instance of it"""
        newnode = nodes.Lambda(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.args, newnode),
                         self.visit(node.body, newnode))
        return newnode

    def visit_list(self, node, parent):
        """visit a List node by returning a fresh instance of it"""
        context = _get_context(node)
        newnode = nodes.List(ctx=context,
                             lineno=node.lineno,
                             col_offset=node.col_offset,
                             parent=parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.elts])
        return newnode

    def visit_listcomp(self, node, parent):
        """visit a ListComp node by returning a fresh instance of it"""
        newnode = nodes.ListComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode),
                         [self.visit(child, newnode)
                          for child in node.generators])
        return newnode

    def visit_name(self, node, parent):
        """visit a Name node by returning a fresh instance of it"""
        context = _get_context(node)
        # True and False can be assigned to something in py2x, so we have to
        # check first the context.
        if context == astroid.Del:
            newnode = nodes.DelName(node.id, node.lineno, node.col_offset,
                                    parent)
        elif context == astroid.Store:
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

    def visit_str(self, node, parent):
        """visit a String/Bytes node by returning a fresh instance of Const"""
        return nodes.Const(node.s, getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None), parent)
    visit_bytes = visit_str

    def visit_num(self, node, parent):
        """visit a Num node by returning a fresh instance of Const"""
        return nodes.Const(node.n, getattr(node, 'lineno', None),
                           getattr(node, 'col_offset', None), parent)

    def visit_pass(self, node, parent):
        """visit a Pass node by returning a fresh instance of it"""
        return nodes.Pass(node.lineno, node.col_offset, parent)

    def visit_print(self, node, parent):
        """visit a Print node by returning a fresh instance of it"""
        newnode = nodes.Print(node.nl, node.lineno, node.col_offset, parent)
        newnode.postinit(_visit_or_empty(node, 'dest', self, newnode),
                         [self.visit(child, newnode)
                          for child in node.values])
        return newnode

    def visit_raise(self, node, parent):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = nodes.Raise(node.lineno, node.col_offset, parent)
        newnode.postinit(_visit_or_empty(node, 'type', self, newnode),
                         _visit_or_empty(node, 'inst', self, newnode),
                         _visit_or_empty(node, 'tback', self, newnode))
        return newnode

    def visit_return(self, node, parent):
        """visit a Return node by returning a fresh instance of it"""
        newnode = nodes.Return(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_set(self, node, parent):
        """visit a Set node by returning a fresh instance of it"""
        newnode = nodes.Set(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.elts])
        return newnode

    def visit_setcomp(self, node, parent):
        """visit a SetComp node by returning a fresh instance of it"""
        newnode = nodes.SetComp(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.elt, newnode),
                         [self.visit(child, newnode)
                          for child in node.generators])
        return newnode

    def visit_slice(self, node, parent):
        """visit a Slice node by returning a fresh instance of it"""
        newnode = nodes.Slice(parent=parent)
        newnode.postinit(_visit_or_empty(node, 'lower', self, newnode),
                         _visit_or_empty(node, 'upper', self, newnode),
                         _visit_or_empty(node, 'step', self, newnode))
        return newnode

    def visit_subscript(self, node, parent):
        """visit a Subscript node by returning a fresh instance of it"""
        context = _get_context(node)
        newnode = nodes.Subscript(ctx=context,
                                  lineno=node.lineno,
                                  col_offset=node.col_offset,
                                  parent=parent)
        newnode.postinit(self.visit(node.value, newnode),
                         self.visit(node.slice, newnode))
        return newnode

    def visit_tryexcept(self, node, parent):
        """visit a TryExcept node by returning a fresh instance of it"""
        newnode = nodes.TryExcept(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.body],
                         [self.visit(child, newnode)
                          for child in node.handlers],
                         [self.visit(child, newnode)
                          for child in node.orelse])
        return newnode

    def visit_tryfinally(self, node, parent):
        """visit a TryFinally node by returning a fresh instance of it"""
        newnode = nodes.TryFinally(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.body],
                         [self.visit(n, newnode)
                          for n in node.finalbody])
        return newnode

    def visit_tuple(self, node, parent):
        """visit a Tuple node by returning a fresh instance of it"""
        context = _get_context(node)
        newnode = nodes.Tuple(ctx=context,
                              lineno=node.lineno,
                              col_offset=node.col_offset,
                              parent=parent)
        newnode.postinit([self.visit(child, newnode)
                          for child in node.elts])
        return newnode

    def visit_unaryop(self, node, parent):
        """visit a UnaryOp node by returning a fresh instance of it"""
        newnode = nodes.UnaryOp(_UNARY_OP_CLASSES[node.op.__class__],
                                node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.operand, newnode))
        return newnode

    def visit_while(self, node, parent):
        """visit a While node by returning a fresh instance of it"""
        newnode = nodes.While(node.lineno, node.col_offset, parent)
        newnode.postinit(self.visit(node.test, newnode),
                         [self.visit(child, newnode)
                          for child in node.body],
                         [self.visit(child, newnode)
                          for child in node.orelse])
        return newnode

    def visit_with(self, node, parent):
        newnode = nodes.With(node.lineno, node.col_offset, parent)
        with_item = nodes.WithItem(node.context_expr.lineno,
                                   node.context_expr.col_offset, newnode)
        context_expr = self.visit(node.context_expr, with_item)
        optional_vars = _visit_or_empty(node, 'optional_vars', self, with_item)
        with_item.postinit(context_expr, optional_vars)
        newnode.postinit([with_item],
                         [self.visit(child, newnode) for child in node.body])
        return newnode

    def visit_yield(self, node, parent):
        """visit a Yield node by returning a fresh instance of it"""
        newnode = nodes.Yield(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode))
        return newnode


class TreeRebuilder3(TreeRebuilder):
    """extend and overwrite TreeRebuilder for python3k"""

    def visit_nameconstant(self, node, parent):
        # in Python 3.4 we have NameConstant for True / False / None
        return nodes.NameConstant(node.value, getattr(node, 'lineno', None),
                                  getattr(node, 'col_offset', None), parent)

    def visit_excepthandler(self, node, parent):
        """visit an ExceptHandler node by returning a fresh instance of it"""
        newnode = nodes.ExceptHandler(node.lineno, node.col_offset, parent)
        if node.name:
            name = self.visit_assignname(node, newnode, node.name)
        else:
            name = nodes.Empty
        newnode.postinit(_visit_or_empty(node, 'type', self, newnode),
                         name,
                         [self.visit(child, newnode)
                          for child in node.body])
        return newnode

    def visit_nonlocal(self, node, parent):
        """visit a Nonlocal node and return a new instance of it"""
        return nodes.Nonlocal(node.names, getattr(node, 'lineno', None),
                              getattr(node, 'col_offset', None), parent)


    def visit_raise(self, node, parent):
        """visit a Raise node by returning a fresh instance of it"""
        newnode = nodes.Raise(node.lineno, node.col_offset, parent)
        # no traceback; anyway it is not used in Pylint
        newnode.postinit(_visit_or_empty(node, 'exc', self, newnode),
                         _visit_or_empty(node, 'cause', self, newnode))
        return newnode

    def visit_starred(self, node, parent):
        """visit a Starred node and return a new instance of it"""
        context = _get_context(node)
        newnode = nodes.Starred(ctx=context, lineno=node.lineno,
                                col_offset=node.col_offset,
                                parent=parent)
        newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_try(self, node, parent):
        # python 3.3 introduce a new Try node replacing
        # TryFinally/TryExcept nodes
        if node.finalbody:
            newnode = nodes.TryFinally(node.lineno, node.col_offset, parent)
            if node.handlers:
                body = [self.visit_tryexcept(node, newnode)]
            else:
                body = [self.visit(child, newnode)
                        for child in node.body]
            newnode.postinit(body,
                             [self.visit(n, newnode)
                              for n in node.finalbody])
            return newnode
        elif node.handlers:
            return self.visit_tryexcept(node, parent)

    def visit_with(self, node, parent, constructor=nodes.With):
        newnode = constructor(node.lineno, node.col_offset, parent)
        newnode.postinit([self.visit(item, newnode) for item in node.items],
                         [self.visit(child, newnode) for child in node.body])
        return newnode

    def visit_withitem(self, node, parent):
        newnode = nodes.WithItem(node.context_expr.lineno,
                                 node.context_expr.col_offset, parent)
        context_expr = self.visit(node.context_expr, newnode)
        optional_vars = _visit_or_empty(node, 'optional_vars', self, newnode)
        newnode.postinit(context_expr=context_expr, optional_vars=optional_vars)
        return newnode

    def visit_yieldfrom(self, node, parent):
        newnode = nodes.YieldFrom(node.lineno, node.col_offset, parent)
        if node.value is not None:
            newnode.postinit(self.visit(node.value, newnode))
        return newnode

    def visit_classdef(self, node, parent, newstyle=True):
        return super(TreeRebuilder3, self).visit_classdef(node, parent,
                                                          newstyle=newstyle)

    # Async structs added in Python 3.5
    def visit_asyncfunctiondef(self, node, parent):
        return self._visit_functiondef(nodes.AsyncFunctionDef, node, parent)

    def visit_asyncfor(self, node, parent):
        return self._visit_for(nodes.AsyncFor, node, parent)

    def visit_await(self, node, parent):
        newnode = nodes.Await(node.lineno, node.col_offset, parent)
        newnode.postinit(value=self.visit(node.value, newnode))
        return newnode

    def visit_asyncwith(self, node, parent):
        return self.visit_with(node, parent, constructor=nodes.AsyncWith)


if sys.version_info >= (3, 0):
    TreeRebuilder = TreeRebuilder3
