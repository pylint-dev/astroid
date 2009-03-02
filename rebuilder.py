#
"""this module contains utilities for rebuilding a compiler.ast
or _ast tree in order to get a single ASTNG representation
"""
from logilab.astng.utils import ASTVisitor
from logilab.astng.raw_building import *
from logilab.astng._exceptions import ASTNGBuildingException, InferenceError
from logilab.astng.nodes import TreeRebuilder
from logilab.astng import nodes
from logilab.astng.nodes_as_string import as_string


class RebuildVisitor(ASTVisitor):
    """Visitor to transform an AST to an ASTNG
    """
    def __init__(self):
        self._asscontext = None
        self._module = None
        self._stack = None
        self._metaclass = None
        self._delayed = []
        self.rebuilder = TreeRebuilder()

    def _add_local(self, node, name):
        if self._global_names and name in self._global_names[-1]:
            node.root().set_local(name, node)
        else:
            node.parent.set_local(name, node)

    def _push(self, node):
        """update the stack and init some parts of the Function or Class node
        """
        obj = getattr(self._stack[-1], node.name, None)
        self._stack.append(obj)
        node.locals = {}
        node.parent.frame().set_local(node.name, node)

    def set_context(self, node, childnode):
        if isinstance(node, nodes.Assign):
            if childnode in node.targets:
                self._asscontext = node
            else:
                self._asscontext = None
        elif isinstance(node, (nodes.AugAssign, nodes.ListCompFor, nodes.For)):
            if childnode is node.target:
                self._asscontext = node
            else:
                self._asscontext = None
        elif isinstance(node, nodes.Subscript):
            self._asscontext = None # XXX disable _asscontext on subscripts ?

    def walk(self, node, parent=None):
        """default visit method, handle the parent attribute"""
        node.parent = parent
        node.accept(self.rebuilder)
        handle_leave = node.accept(self)
        for child in node.get_children():
            self.set_context(node, child)
            self.walk(child, node)
        if handle_leave:
            leave = getattr(self, "leave_" + node.__class__.__name__.lower() )
            leave(node)

    # general visit_<node> methods ############################################
    
    def visit_assign(self, node):
        return True
    
    def leave_assign(self, node):
        """leave an Assign node to become astng"""
        klass = node.parent.frame()
        if isinstance(klass, nodes.Class) and \
            isinstance(node.value, nodes.CallFunc) and \
            isinstance(node.value.func, nodes.Name):
            func_name = node.value.func.name
            if func_name in ('classmethod', 'staticmethod'):
                for ass_node in node.targets:
                    try:
                        meth = klass[ass_node.name]
                        if isinstance(meth, nodes.Function):
                            meth.type = func_name
                    except (AttributeError, KeyError):
                        continue
        elif getattr(node.targets[0], 'name', None) == '__metaclass__': # XXX check more...
            self._metaclass[-1] = 'type' # XXX get the actual metaclass

    def visit_class(self, node):
        """visit an Class node to become astng"""
        node.instance_attrs = {}
        self._push(node)
        for name, value in ( ('__name__', node.name),
                             ('__module__', node.root().name),
                             ('__doc__', node.doc) ):
            const = nodes.const_factory(value)
            const.parent = node
            node.locals[name] = [const]
        attach___dict__(node)
        self._metaclass.append(self._metaclass[-1])
        return True

    def leave_class(self, node):
        """leave a Class node -> pop the last item on the stack"""
        self._stack.pop()
        metaclass = self._metaclass.pop()
        if not node.bases:
            # no base classes, detect new / style old style according to
            # current scope
            node._newstyle = metaclass == 'type'
        node.basenames = [as_string(bnode) for bnode in node.bases]
    
    leave_classdef = leave_class

    def visit_decorators(self, node):
        """visiting an Decorators node: return True for leaving"""
        return True

    def leave_decorators(self, node):
        """python >= 2.4
        visit a Decorator node -> check for classmethod and staticmethod
        """
        for decorator_expr in node.items:
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
        register_arguments(node, node.argnames)
        return True

    def leave_function(self, node):
        """leave a Function node -> pop the last item on the stack"""
        self._stack.pop()
        self._global_names.pop()
    leave_functiondef = leave_function

    def visit_genexpr(self, node):
        """visit an ListComp node to become astng"""
        node.locals = {}

    def visit_getattr(self, node):
        """visit an Getattr node to become astng"""
        self._delayed.append(node) # FIXME

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
        register_arguments(node, node.argnames)

    def visit_module(self, node):
        """visit an Module node to become astng"""
        self._stack = [self._module]
        self._metaclass = ['']
        self._global_names = []
        node.globals = node.locals = {}
        for name, value in ( ('__name__', node.name),
                             ('__file__', node.path),
                             ('__doc__', node.doc) ):
            const = nodes.const_factory(value)
            const.parent = node
            node.locals[name] = [const]
        if node.package:
            # FIXME: List(Const())
            const = nodes.const_factory(value)
            const.parent = node
            node.locals['__path__'] = [const]
        return True

    def leave_module(self, _):
        """leave a Module node -> pop the last item on the stack and check
        the stack is empty
        """
        self._stack.pop()
        assert not self._stack, 'Stack is not empty : %s' % self._stack

    def visit_name(self, node):
        """visit an Name node to become astng"""
        try:
            cls, value = nodes.CONST_NAME_TRANSFORMS[node.name]
            node.__class__ = cls
            node.value = value
        except KeyError:
            pass
        if self._asscontext is not None:
            self._add_local(self._asscontext, node.name)

    # # delayed methods


    def delayed_visit_getattr(self, node):
        """visit a AssAttr/ GetAttr node -> add name to locals, handle members
        definition
        """
        return # XXX
        try:
            frame = node.frame()
            for infered in node.expr.infer():
                if infered is nodes.YES:
                    continue
                try:
                    if infered.__class__ is nodes.Instance:
                        infered = infered._proxied
                        iattrs = infered.instance_attrs
                    else:
                        iattrs = infered.locals
                except AttributeError:
                    import traceback
                    traceback.print_exc()
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
