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
"""this module contains utilities for rebuilding a compiler.ast or _ast tree in
order to get a single ASTNG representation

:author:    Sylvain Thenault
:copyright: 2008-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2008-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from logilab.astng import ASTNGBuildingException, InferenceError
from logilab.astng import nodes
from logilab.astng.utils import ASTVisitor, REDIRECT
from logilab.astng.infutils import YES, Instance


CONST_NAME_TRANSFORMS = {'None':  None,
                         'True':  True,
                         'False': False}

def _check_children(node):
    """a helper function to check children - parent relations"""
    for child in node.get_children():
        if not hasattr(child, 'parent'):
            print " ERROR: %s has child %s %x with no parent" % (node, child, id(child))
        elif not child.parent:
            print " ERROR: %s has child %s %x with parent %r" % (node, child, id(child), child.parent)
        elif child.parent is not node:
            print " ERROR: %s %x has child %s %x with wrong parent %s" % (node,
                                      id(node), child, id(child), child.parent)
        _check_children(child)


class RebuildVisitor(ASTVisitor):
    """Visitor to transform an AST to an ASTNG
    """
    def __init__(self, ast_mode):
        self.asscontext = None
        self._metaclass = None
        self._global_names = None
        self._delayed = dict((name, []) for name in ('class', 'function',
                              'assattr', 'assign', 'decorators', 'from'))
        self.set_line_info = (ast_mode == '_ast')
        self._ast_mode = (ast_mode == '_ast')
        self._assignments = []

    def visit(self, node, parent):
        if node is None: # some attributes of some nodes are just None
            return None
        # TODO : parent is never used; replace by newparent ? Could
        #        replace set_infos or simplify some other cases ?
        cls_name = node.__class__.__name__
        _method_suffix = REDIRECT.get(cls_name, cls_name).lower()

        _visit = getattr(self, "visit_%s" % _method_suffix )
        newnode = _visit(node)
        if newnode is None:
            return
        self.set_infos(newnode, node)
        return newnode

    def set_infos(self, newnode, oldnode):
        """set parent and line number infos"""
        # some nodes are created by the TreeRebuilder without going through
        # the visit method; hence we have to set infos explicitly at different
        # places
        child = None
        for child in newnode.get_children():
            if child is not None:
                child.parent = newnode
            else:
                print "newnode %s has None as child" % newnode
        # line info setting
        # XXX We don't necessarily get the same type of node back as Rebuilding
        # inserts nodes of different type and returns them... Is it a problem ?
        if hasattr(oldnode, 'lineno'):
            newnode.lineno = oldnode.lineno
        if self.set_line_info: # _ast
            newnode.set_line_info(child)
        else: # compiler
            if hasattr(oldnode, 'fromlineno'):
                newnode.fromlineno = oldnode.fromlineno
            if hasattr(oldnode, 'tolineno'):
                newnode.tolineno = oldnode.tolineno

    def walk(self, node):
        """start the walk down the tree and do some work after it"""
        newnode = self.visit(node, None)
        _check_children(newnode) # FIXME : remove this asap
        # handle delayed nodes; assattr has to be done at last since it needs
        # some inference which is only possible once the node.locals set
        for name, nodes in self._delayed.items():
            if name == 'assattr':
                continue
            delay_method = getattr(self, 'delayed_' + name)
            for node in nodes:
                delay_method(node)
        for assnode, name, root_local in self._assignments:
            if root_local:
                assnode.root().set_local(name, assnode)
            else:
                # _check_children(assnode)
                # print assnode, id(assnode)
                if assnode.parent is not None:
                    assnode.parent.set_local(name, assnode)

        delay_assattr = self.delayed_assattr
        for node in self._delayed['assattr']:
            delay_assattr(node)
        return newnode

    def _save_argument_name(self, node):
        """save argument names for setting locals"""
        if node.vararg:
            self._assignments.append((node, node.vararg, False))
        if node.kwarg:
            self._assignments.append((node, node.kwarg, False))


    # visit_<node> and delayed_<node> methods #################################

    def visit_assign(self, node):
        newnode = self._visit_assign(node)
        self._delayed['assign'].append(newnode)
        return newnode

    def delayed_assign(self, newnode):
        klass = newnode.parent.frame()
        if (isinstance(klass, nodes.Class)
            and isinstance(newnode.value, nodes.CallFunc)
            and isinstance(newnode.value.func, nodes.Name)):
            func_name = newnode.value.func.name
            for ass_node in newnode.targets:
                try:
                    meth = klass[ass_node.name]
                    if isinstance(meth, nodes.Function):
                        if func_name in ('classmethod', 'staticmethod'):
                            meth.type = func_name
                        try: # XXX use setdefault ?
                            meth.extra_decorators.append(newnode.value)
                        except AttributeError:
                            meth.extra_decorators = [newnode.value]
                except (AttributeError, KeyError):
                    continue
        elif getattr(newnode.targets[0], 'name', None) == '__metaclass__':
            # XXX check more...
            self._metaclass[-1] = 'type' # XXX get the actual metaclass
        return newnode

    def visit_class(self, node):
        """visit a Class node to become astng"""
        self._metaclass.append(self._metaclass[-1])
        newnode = self._visit_class(node)
        newnode.name = node.name
        metaclass = self._metaclass.pop()
        if not newnode.bases:
            # no base classes, detect new / style old style according to
            # current scope
            newnode._newstyle = metaclass == 'type'
        self._delayed['class'].append(newnode)
        return newnode

    def delayed_class(self, node):
        node.parent.frame().set_local(node.name, node)

    def visit_const(self, node):
        """visit a Const node by returning a fresh instance of it"""
        newnode = nodes.Const(node.value)
        return newnode

    def visit_continue(self, node):
        """visit a Continue node by returning a fresh instance of it"""
        newnode = nodes.Continue()
        return newnode

    def visit_decorators(self, node):
        """visiting an Decorators node"""
        newnode = self._visit_decorators(node)
        self._delayed['decorators'].append(newnode)
        return newnode

    def delayed_decorators(self, node):
        """python >= 2.4
        visit a Decorator node -> check for classmethod and staticmethod
        """
        for decorator_expr in node.nodes:
            if isinstance(decorator_expr, nodes.Name) and \
                   decorator_expr.name in ('classmethod', 'staticmethod'):
                node.parent.type = decorator_expr.name

    def visit_ellipsis(self, node):
        """visit an Ellipsis node by returning a fresh instance of it"""
        newnode = nodes.Ellipsis()
        return newnode

    def visit_emptynode(self, node):
        """visit an EmptyNode node by returning a fresh instance of it"""
        newnode = nodes.EmptyNode()
        return newnode

    def delayed_from(self, node):
        """visit an From node to become astng"""
        # add names imported by the import to locals
        for (name, asname) in node.names:
            if name == '*':
                try:
                    imported = node.root().import_module(node.modname)
                except ASTNGBuildingException:
                    continue
                for name in imported.wildcard_import_names():
                    node.parent.set_local(name, node)
            else:
                node.parent.set_local(asname or name, node)

    def visit_function(self, node):
        """visit an Function node to become astng"""
        self._global_names.append({})
        newnode = self._visit_function(node)
        self._delayed['function'].append(newnode)
        newnode.name = node.name
        self._global_names.pop()
        return newnode

    def delayed_function(self, newnode):
        frame = newnode.parent.frame()
        if isinstance(frame, nodes.Class):
            if newnode.name == '__new__':
                newnode.type = 'classmethod'
            else:
                newnode.type = 'method'
        frame.set_local(newnode.name, newnode)

    def visit_global(self, node):
        """visit an Global node to become astng"""
        newnode = nodes.Global(node.names)
        if self._global_names: # global at the module level, no effect
            for name in node.names:
                self._global_names[-1].setdefault(name, []).append(newnode)
        return newnode

    def _save_import_locals(self, newnode):
        """save import names to set them in locals later on"""
        for (name, asname) in newnode.names:
            name = asname or name
            self._assignments.append( (newnode, name.split('.')[0], False) )

    def visit_module(self, node):
        """visit an Module node to become astng"""
        self._metaclass = ['']
        self._global_names = []
        return self._visit_module(node)

    def visit_name(self, node):
        """visit an Name node to become astng"""
        newnode = self._visit_name(node)
        if newnode.name in CONST_NAME_TRANSFORMS:
            return nodes.Const(CONST_NAME_TRANSFORMS[newnode.name])
        return newnode

    def visit_pass(self, node):
        """visit a Pass node by returning a fresh instance of it"""
        newnode = nodes.Pass()
        return newnode

    def _save_assignment(self, node, name=None):
        """save assignement situation since node.parent is not available yet"""
        if self._global_names and node.name in self._global_names[-1]:
            self._assignments.append((node, node.name, True))
        else:
            self._assignments.append((node, node.name, False))

    def delayed_assattr(self, node):
        """visit a AssAttr node -> add name to locals, handle members
        definition
        """
        try:
            frame = node.frame()
            for infered in node.expr.infer():
                if infered is YES:
                    continue
                try:
                    if infered.__class__ is Instance:
                        infered = infered._proxied
                        iattrs = infered.instance_attrs
                    elif isinstance(infered, Instance):
                        # Const, Tuple, ... we may be wrong, may be not, but
                        # anyway we don't want to pollute builtin's namespace
                        continue
                    else:
                        iattrs = infered.locals
                except AttributeError:
                    # XXX log error
                    #import traceback
                    #traceback.print_exc()
                    continue
                values = iattrs.setdefault(node.attrname, [])
                if node in values:
                    continue
                # get assign in __init__ first XXX useful ?
                if frame.name == '__init__' and values and not \
                       values[0].frame().name == '__init__':
                    values.insert(0, node)
                else:
                    values.append(node)
        except InferenceError:
            pass

    # --- additional methods ----

    def _build_excepthandler(self, node, exctype, excobj, body):
        newnode = nodes.ExceptHandler()
        newnode.type = self.visit(exctype, node)
        self.asscontext = "Ass"
        newnode.name = self.visit(excobj, node)
        self.asscontext = None
        newnode.body = [self.visit(child, node) for child in body]
        self.set_infos(newnode, node)
        return newnode

