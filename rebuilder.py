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

from logilab.astng import ASTNGBuildingException, InferenceError, NodeRemoved
from logilab.astng import nodes
from logilab.astng.utils import ASTVisitor
from logilab.astng.infutils import YES, Instance


CONST_NAME_TRANSFORMS = {'None':  (nodes.Const, None),
                         'True':  (nodes.Const, True),
                         'False': (nodes.Const, False)}

class RebuildVisitor(ASTVisitor):
    """Visitor to transform an AST to an ASTNG
    """
    def __init__(self):
        self.asscontext = None
        self._metaclass = None
        self._global_names = None
        self._delayed = []
        self.rebuilder = nodes.TreeRebuilder(self)
        self.set_line_info = nodes.AST_MODE == '_ast'

    def _push(self, node):
        """update the stack and init some parts of the Function or Class node
        """
        node.locals = {}
        node.parent.frame().set_local(node.name, node)

    def set_asscontext(self, node, childnode):
        """set assignment /delete context needed later on by the childnode"""
        # XXX refactor this method at least, but killing .asscontext  would be better
        if isinstance(node, (nodes.Delete, nodes.Assign)):
            if childnode in node.targets:
                self.asscontext = node
            else:
                self.asscontext = None
        elif isinstance(node, (nodes.AugAssign, nodes.Comprehension, nodes.For)):
            if childnode is node.target:
                self.asscontext = node
            else:
                self.asscontext = None
        elif isinstance(node, nodes.Arguments):
            if childnode in node.args:
                self.asscontext = node
            else:
                self.asscontext = None
        elif isinstance(node, nodes.With):
            if childnode is node.vars:
                self.asscontext = node
            else:
                self.asscontext = None
        elif isinstance(node, nodes.ExceptHandler):
            if childnode is node.name:
                self.asscontext = node
            else:
                self.asscontext = None

    # take node arguments to be usable as visit/leave methods
    def push_asscontext(self, node=None):
        self.__asscontext = self.asscontext
        self.asscontext = None
        return True
    def pop_asscontext(self, node=None):
        self.asscontext = self.__asscontext
        self.__asscontext = None

    def walk(self, node):
        self._walk(node)
        delayed = self._delayed
        while delayed:
            dnode = delayed.pop(0)
            node_name = dnode.__class__.__name__.lower()
            self.delayed_visit_assattr(dnode)

    def _walk(self, node, parent=None):
        """default visit method, handle the parent attribute"""
        node.parent = parent
        try:
            node.accept(self.rebuilder)
        except NodeRemoved:
            return
        handle_leave = node.accept(self)
        child = None
        # XXX tuple necessary since node removal may modify children
        #     find a trick to avoid tuple() or make get_children() returning a list)
        for child in tuple(node.get_children()):
            self.set_asscontext(node, child)
            self._walk(child, node)
            if self.asscontext is child:
                self.asscontext = None
        if self.set_line_info:
            node.set_line_info(child)
        if handle_leave:
            leave = getattr(self, "leave_" + node.__class__.__name__.lower())
            leave(node)
        

    # general visit_<node> methods ############################################

    def visit_arguments(self, node):
        if node.vararg:
            node.parent.set_local(node.vararg, node)
        if node.kwarg:
            node.parent.set_local(node.kwarg, node)

    def visit_assign(self, node):
        return True

    def leave_assign(self, node):
        """leave an Assign node to become astng"""
        klass = node.parent.frame()
        if (isinstance(klass, nodes.Class)
            and isinstance(node.value, nodes.CallFunc)
            and isinstance(node.value.func, nodes.Name)):
            func_name = node.value.func.name
            for ass_node in node.targets:
                try:
                    meth = klass[ass_node.name]
                    if isinstance(meth, nodes.Function):
                        if func_name in ('classmethod', 'staticmethod'):
                            meth.type = func_name
                        try:
                            meth.extra_decorators.append(node.value)
                        except AttributeError:
                            meth.extra_decorators = [node.value]
                except (AttributeError, KeyError):
                    continue
        elif getattr(node.targets[0], 'name', None) == '__metaclass__': # XXX check more...
            self._metaclass[-1] = 'type' # XXX get the actual metaclass

    def visit_class(self, node):
        """visit an Class node to become astng"""
        node.instance_attrs = {}
        self._push(node)
        self._metaclass.append(self._metaclass[-1])
        return True

    def leave_class(self, node):
        """leave a Class node -> pop the last item on the stack"""
        metaclass = self._metaclass.pop()
        if not node.bases:
            # no base classes, detect new / style old style according to
            # current scope
            node._newstyle = metaclass == 'type'
    
    leave_classdef = leave_class

    def visit_decorators(self, node):
        """visiting an Decorators node: return True for leaving"""
        return True

    def leave_decorators(self, node):
        """python >= 2.4
        visit a Decorator node -> check for classmethod and staticmethod
        """
        for decorator_expr in node.nodes:
            if isinstance(decorator_expr, nodes.Name) and \
                   decorator_expr.name in ('classmethod', 'staticmethod'):
                node.parent.type = decorator_expr.name

    def visit_from(self, node):
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
        if isinstance(node.parent.frame(), nodes.Class):
            if node.name == '__new__':
                node.type = 'classmethod'
            else:
                node.type = 'method'
        self._push(node)
        return True

    def leave_function(self, node):
        """leave a Function node -> pop the last item on the stack"""
        self._global_names.pop()
    leave_functiondef = leave_function

    def visit_genexpr(self, node):
        """visit an ListComp node to become astng"""
        node.locals = {}

    def visit_assattr(self, node):
        """visit an Getattr node to become astng"""
        self._delayed.append(node) # FIXME
        self.push_asscontext()
        return True        
    visit_delattr = visit_assattr
    
    def leave_assattr(self, node):
        """visit an Getattr node to become astng"""
        self._delayed.append(node) # FIXME
        self.pop_asscontext()
    leave_delattr = leave_assattr
    
    def visit_global(self, node):
        """visit an Global node to become astng"""
        if not self._global_names: # global at the module level, no effect
            return
        for name in node.names:
            self._global_names[-1].setdefault(name, []).append(node)

    def visit_import(self, node):
        """visit an Import node to become astng"""
        for (name, asname) in node.names:
            name = asname or name
            node.parent.set_local(name.split('.')[0], node)

    def visit_lambda(self, node):
        """visit an Keyword node to become astng"""
        node.locals = {}

    def visit_module(self, node):
        """visit an Module node to become astng"""
        self._metaclass = ['']
        self._global_names = []
        node.globals = node.locals = {}
        
    def visit_name(self, node):
        """visit an Name node to become astng"""
        try:
            cls, value = CONST_NAME_TRANSFORMS[node.name]
            node.__class__ = cls
            node.value = value
        except KeyError:
            pass

    def visit_assname(self, node):
        if self.asscontext is not None:
            if self._global_names and node.name in self._global_names[-1]:
                node.root().set_local(node.name, node)
            else:
                node.parent.set_local(node.name, node)
    visit_delname = visit_assname

    visit_subscript = push_asscontext
    leave_subscript = pop_asscontext
    
    def delayed_visit_assattr(self, node):
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
