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
"""This module extends ast "scoped" node, i.e. which are opening a new
local scope in the language definition : Module, Class, Function (and
Lambda in some extends).

Each new methods and attributes added on each class are documented
below.


:author:    Sylvain Thenault
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2007 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""
from __future__ import generators

__doctype__ = "restructuredtext en"

import sys

from logilab.common.compat import chain, set

from logilab.astng.utils import extend_class
from logilab.astng import YES, MANAGER, Instance, InferenceContext, copy_context, \
     unpack_infer, _infer_stmts, \
     Class, Const, Dict, Function, GenExpr, Lambda, From, \
     Module, Name, Pass, Raise, Tuple, Yield
from logilab.astng import NotFoundError, NoDefault, \
     ASTNGBuildingException, InferenceError

# module class dict/iterator interface ########################################
    
class LocalsDictMixIn(object):
    """ this class provides locals handling common to Module, Function
    and Class nodes, including a dict like interface for direct access
    to locals information
    
    /!\ this class should not be used directly /!\ it's
    only used as a methods and attribute container, and update the
    original class from the compiler.ast module using its dictionnary
    (see below the class definition)
    """
    
    # attributes below are set by the builder module or by raw factories
    
    # dictionary of locals with name as key and node defining the local as
    # value    
    locals = None

    def qname(self):
        """return the 'qualified' name of the node, eg module.name,
        module.class.name ...
        """
        if self.parent is None:
            return self.name
        return '%s.%s' % (self.parent.frame().qname(), self.name)
        
    def frame(self):
        """return the first parent frame node (i.e. Module, Function or Class)
        """
        return self
    
    def scope(self):
        """return the first node defining a new scope (i.e. Module,
        Function, Class, Lambda but also GenExpr)
        """
        return self
    
    def set_local(self, name, stmt):
        """define <name> in locals (<stmt> is the node defining the name)
        if the node is a Module node (i.e. has globals), add the name to
        globals

        if the name is already defined, ignore it
        """
        self.locals.setdefault(name, []).append(stmt)
        
    __setitem__ = set_local
    
    def add_local_node(self, child_node, name=None):
        """append a child which should alter locals to the given node"""
        if name != '__class__':
            # add __class__ node as a child will cause infinite recursion later!
            self._append_node(child_node)
        self.set_local(name or child_node.name, child_node)

    def _append_node(self, child_node):
        """append a child, linking it in the tree"""
        self.code.nodes.append(child_node)
        child_node.parent = self
    
    def __getitem__(self, item):
        """method from the `dict` interface returning the first node
        associated with the given name in the locals dictionnary

        :type item: str
        :param item: the name of the locally defined object
        :raises KeyError: if the name is not defined
        """
        return self.locals[item][0]
    
    def __iter__(self):
        """method from the `dict` interface returning an iterator on
        `self.keys()`
        """
        return iter(self.keys())
    
    def keys(self):
        """method from the `dict` interface returning a tuple containing
        locally defined names
        """
        return self.locals.keys()
##         associated to nodes which are instance of `Function` or
##         `Class`
##         """
##         # FIXME: sort keys according to line number ?
##         try:
##             return self.__keys
##         except AttributeError:
##             keys = [member.name for member in self.locals.values()
##                     if (isinstance(member, Function)
##                         or isinstance(member, Class))
##                         and member.parent.frame() is self]
##             self.__keys = tuple(keys)
##             return keys

    def values(self):
        """method from the `dict` interface returning a tuple containing
        locally defined nodes which are instance of `Function` or `Class`
        """
        return [self[key] for key in self.keys()]
    
    def items(self):
        """method from the `dict` interface returning a list of tuple
        containing each locally defined name with its associated node,
        which is an instance of `Function` or `Class`
        """
        return zip(self.keys(), self.values())

    def has_key(self, name):
        """method from the `dict` interface returning True if the given
        name is defined in the locals dictionary
        """
        return self.locals.has_key(name)
    
    __contains__ = has_key
    
extend_class(Module, LocalsDictMixIn)
extend_class(Class, LocalsDictMixIn)
extend_class(Function, LocalsDictMixIn)
extend_class(Lambda, LocalsDictMixIn)
# GenExpr has it's own locals but isn't a frame
extend_class(GenExpr, LocalsDictMixIn)
def frame(self):
    return self.parent.frame()
GenExpr.frame = frame


class GetattrMixIn(object):
    def getattr(self, name, context=None):
        try:
            return self.locals[name]
        except KeyError:
            raise NotFoundError(name)
        
    def igetattr(self, name, context=None):
        """infered getattr"""
        # set lookup name since this is necessary to infer on import nodes for
        # instance
        context = copy_context(context)
        context.lookupname = name
        try:
            return _infer_stmts(self.getattr(name, context), context, frame=self)
        except NotFoundError:
            raise InferenceError(name)
extend_class(Module, GetattrMixIn)
extend_class(Class, GetattrMixIn)

# Module  #####################################################################

class ModuleNG(object):
    """/!\ this class should not be used directly /!\ it's
    only used as a methods and attribute container, and update the
    original class from the compiler.ast module using its dictionnary
    (see below the class definition)
    """
        
    # attributes below are set by the builder module or by raw factories

    # the file from which as been extracted the astng representation. It may
    # be None if the representation has been built from a built-in module
    file = None
    # the module name
    name = None
    # boolean for astng built from source (i.e. ast)
    pure_python = None
    # boolean for package module
    package = None
    # dictionary of globals with name as key and node defining the global
    # as value
    globals = None

    def pytype(self):
        return '__builtin__.module'
    
    def getattr(self, name, context=None):
        try:
            return self.locals[name]
        except KeyError:
            if self.package:
                try:
                    return [self.import_module(name, relative_only=True)]
                except KeyboardInterrupt:
                    raise
                except:
                    pass
            raise NotFoundError(name)
        
    def _append_node(self, child_node):
        """append a child version specific to Module node"""
        self.node.nodes.append(child_node)
        child_node.parent = self
        
    def source_line(self):
        """return the source line number, 0 on a module"""
        return 0

    def fully_defined(self):
        """return True if this module has been built from a .py file
        and so contains a complete representation including the code
        """
        return self.file is not None and self.file.endswith('.py')
    
    def statement(self):
        """return the first parent node marked as statement node
        consider a module as a statement...
        """
        return self

    def absolute_import_activated(self):
        for stmt in self.locals.get('absolute_import', ()):
            if isinstance(stmt, From) and stmt.modname == '__future__':
                return True
        return False
    
    def import_module(self, modname, relative_only=False, level=None):
        """import the given module considering self as context"""
        try:
            return MANAGER.astng_from_module_name(self.relative_name(modname, level))
        except ASTNGBuildingException:
            if relative_only:
                raise
        module = MANAGER.astng_from_module_name(modname)
        return module

    def relative_name(self, modname, level):
        if self.absolute_import_activated() and not level:
            return modname
        if level:
            parts = self.name.split('.')
            if self.package:
                parts.append('__init__')
            package_name = '.'.join(parts[:-level])
        elif self.package:
            package_name = self.name
        else:
            package_name = '.'.join(self.name.split('.')[:-1])
        if package_name:
            return '%s.%s' % (package_name, modname)
        return modname
        
    def wildcard_import_names(self):
        """return the list of imported names when this module is 'wildard
        imported'

        It doesn't include the '__builtins__' name which is added by the
        current CPython implementation of wildcard imports.
        """
        # take advantage of a living module if it exists
        try:
            living = sys.modules[self.name]
        except KeyError:
            pass
        else:
            try:
                return living.__all__
            except AttributeError:
                return [name for name in living.__dict__.keys()
                        if not name.startswith('_')]
        # else lookup the astng
        try:
            explicit = self['__all__'].assigned_stmts().next()
            # should be a tuple of constant string
            return [const.value for const in explicit.nodes]
        except (KeyError, AttributeError, InferenceError):
            # XXX should admit we have lost if there is something like
            # __all__ that we've not been able to analyse (such as
            # dynamically constructed __all__)
            return [name for name in self.keys()
                    if not name.startswith('_')]

extend_class(Module, ModuleNG)

# Function  ###################################################################

class FunctionNG(object):
    """/!\ this class should not be used directly /!\ it's
    only used as a methods and attribute container, and update the
    original class from the compiler.ast module using its dictionnary
    (see below the class definition)
    """

    # attributes below are set by the builder module or by raw factories

    # function's type, 'function' | 'method' | 'staticmethod' | 'classmethod'
    type = 'function'
    # list of argument names. MAY BE NONE on some builtin functions where
    # arguments are unknown
    argnames = None

    def pytype(self):
        if 'method' in self.type:
            return '__builtin__.instancemethod'
        return '__builtin__.function'

    def is_method(self):
        """return true if the function node should be considered as a method"""
        # isinstance to avoid returning True on functions decorated by
        # [static|class]method at the module level
        return self.type != 'function' and isinstance(self.parent.frame(), Class)
    
    def is_bound(self):
        """return true if the function is bound to an Instance or a class"""
        return self.type == 'classmethod'

    def is_abstract(self, pass_is_abstract=True):
        """return true if the method is abstract
        It's considered as abstract if the only statement is a raise of
        NotImplementError, or, if pass_is_abstract, a pass statement
        """
        for child_node in self.code.getChildNodes():
            if isinstance(child_node, Raise) and child_node.expr1:
                try:
                    name = child_node.expr1.nodes_of_class(Name).next()
                    if name.name == 'NotImplementedError':
                        return True
                except StopIteration:
                    pass
            if pass_is_abstract and isinstance(child_node, Pass):
                return True
            return False
        # empty function is the same as function with a single "pass" statement
        if pass_is_abstract:
            return True

    def is_generator(self):
        """return true if this is a generator function"""
        try:
            return self.nodes_of_class(Yield, skip_klass=Function).next()
        except StopIteration:
            return False
        
    def format_args(self):
        """return arguments formatted as string"""
        if self.argnames is None: # information is missing
            return ''
        result = []
        args, kwargs, last, default_idx = self._pos_information()
        for i in range(len(self.argnames)):
            name = self.argnames[i]
            if type(name) is type(()):
                name = '(%s)' % ','.join(name)
            if i == last and kwargs:
                name = '**%s' % name
            elif args and i == last or (kwargs and i == last - 1):
                name = '*%s' % name
            elif i >= default_idx:
                default_str = self.defaults[i - default_idx].as_string()
                name = '%s=%s' % (name, default_str)
            result.append(name)
        return ', '.join(result)

    def default_value(self, argname):
        """return the default value for an argument

        :raise `NoDefault`: if there is no default value defined
        """
        if self.argnames is None: # information is missing
            raise NoDefault()
        args, kwargs, last, defaultidx = self._pos_information()
        try:
            i = self.argnames.index(argname)
        except ValueError:
            raise NoDefault() # XXX
        if i >= defaultidx and (i - defaultidx) < len(self.defaults):
            return self.defaults[i - defaultidx]
        raise NoDefault()

    def mularg_class(self, argname):
        """if the given argument is a * or ** argument, return respectivly
        a Tuple or Dict instance, else return None
        """
        args, kwargs, last, defaultidx = self._pos_information()
        try:
            i = self.argnames.index(argname)
        except ValueError:
            return None # XXX
        if i == last and kwargs:
            valnode = Dict([])
            valnode.parent = self
            return valnode
        if args and (i == last or (kwargs and i == last - 1)):
            valnode = Tuple([])
            valnode.parent = self
            return valnode
        return None

    def _pos_information(self):
        """return a 4-uple with positional information about arguments:
        (true if * is used,
         true if ** is used,
         index of the last argument,
         index of the first argument having a default value)
        """
        args = self.flags & 4
        kwargs = self.flags & 8
        last = len(self.argnames) - 1
        defaultidx = len(self.argnames) - (len(self.defaults) +
                                           (args and 1 or 0) +
                                           (kwargs and 1 or 0))
        return args, kwargs, last, defaultidx

extend_class(Function, FunctionNG)

# lambda nodes may also need some of the function members
Lambda._pos_information = FunctionNG._pos_information.im_func
Lambda.format_args = FunctionNG.format_args.im_func
Lambda.default_value = FunctionNG.default_value.im_func
Lambda.mularg_class = FunctionNG.mularg_class.im_func
Lambda.type = 'function'
Lambda.pytype = FunctionNG.pytype.im_func

# Class ######################################################################

def _class_type(klass):
    """return a Class node type to differ metaclass, interface and exception
    from 'regular' classes
    """
    if klass._type is not None:
        return klass._type
    if klass.name == 'type':
        klass._type = 'metaclass'
    elif klass.name.endswith('Interface'):
        klass._type = 'interface'
    elif klass.name.endswith('Exception'):
        klass._type = 'exception'
    else:
        for base in klass.ancestors(recurs=False):
            if base.type != 'class':
                klass._type = base.type
                break
    if klass._type is None:
        klass._type = 'class'
    return klass._type

def _iface_hdlr(iface_node):
    """a handler function used by interfaces to handle suspicious
    interface nodes
    """
    return True

class ClassNG(object):
    """/!\ this class should not be used directly /!\ it's
    only used as a methods and attribute container, and update the
    original class from the compiler.ast module using its dictionnary
    (see below the class definition)
    """
    
    _type = None
    type = property(_class_type,
                    doc="class'type, possible values are 'class' | "
                    "'metaclass' | 'interface' | 'exception'")
    
    def _newstyle_impl(self, context=None):
        context = context or InferenceContext()
        if self._newstyle is not None:
            return self._newstyle
        for base in self.ancestors(recurs=False, context=context):
            if base._newstyle_impl(context):
                self._newstyle = True
                break
        if self._newstyle is None:
            self._newstyle = False
        return self._newstyle

    _newstyle = None
    newstyle = property(_newstyle_impl,
                        doc="boolean indicating if it's a new style class"
                        "or not")

    def pytype(self):
        if self.newstyle:
            return '__builtin__.type'
        return '__builtin__.classobj'
    
    # attributes below are set by the builder module or by raw factories
    
    # a dictionary of class instances attributes
    instance_attrs = None
    # list of parent class as a list of string (ie names as they appears
    # in the class definition)
    basenames = None

    def ancestors(self, recurs=True, context=None):
        """return an iterator on the node base classes in a prefixed
        depth first order
        
        :param recurs:
          boolean indicating if it should recurse or return direct
          ancestors only
        """
        # FIXME: should be possible to choose the resolution order
        # XXX inference make infinite loops possible here (see BaseTransformer
        # manipulation in the builder module for instance !)
        context = context or InferenceContext()
        for stmt in self.bases:
            try:
                for baseobj in stmt.infer(context):
                    if not isinstance(baseobj, Class):
                        # duh ?
                        continue
                    if baseobj is self:
                        continue # cf xxx above
                    yield baseobj
                    if recurs:
                        for grandpa in baseobj.ancestors(True, context):
                            if grandpa is self:
                                continue # cf xxx above
                            yield grandpa
            except InferenceError:
                #import traceback
                #traceback.print_exc()
                # XXX log error ?
                continue
            
    def local_attr_ancestors(self, name, context=None):
        """return an iterator on astng representation of parent classes
        which have <name> defined in their locals
        """
        for astng in self.ancestors(context=context):
            if astng.locals.has_key(name):
                yield astng

    def instance_attr_ancestors(self, name, context=None):
        """return an iterator on astng representation of parent classes
        which have <name> defined in their instance attribute dictionary
        """
        for astng in self.ancestors(context=context):
            if astng.instance_attrs.has_key(name):
                yield astng

    def local_attr(self, name, context=None):
        """return the astng associated to name in this class locals or
        in its parents

        :raises `NotFoundError`:
          if no attribute with this name has been find in this class or
          its parent classes
        """
        try:
            return self[name]
        except KeyError:
            # get if from the first parent implementing it if any
            for class_node in self.local_attr_ancestors(name, context):
                return class_node[name]
        raise NotFoundError(name)
        
    def instance_attr(self, name, context=None):
        """return the astng nodes associated to name in this class instance
        attributes dictionary or in its parents

        :raises `NotFoundError`:
          if no attribute with this name has been find in this class or
          its parent classes
        """
        try:
            return self.instance_attrs[name]
        except KeyError:
            # get if from the first parent implementing it if any
            for class_node in self.instance_attr_ancestors(name, context):
                return class_node.instance_attrs[name]
        raise NotFoundError(name)

    def getattr(self, name, context=None):
        """this method doesn't look in the instance_attrs dictionary since it's
        done by an Instance proxy at inference time.
        
        It may return a YES object if the attribute has not been actually
        found but a __getattr__ or __getattribute__ method is defined
        """
        if name in self.locals:
            return self.locals[name]
        if name == '__bases__':
            return tuple(self.ancestors(recurs=False))
        # XXX need proper meta class handling + MRO implementation
        if name == '__mro__':
            return tuple(self.ancestors(recurs=True))
        for classnode in self.ancestors(recurs=False, context=context):
            try:
                return classnode.getattr(name, context)
            except NotFoundError:
                continue
        raise NotFoundError(name)

    def igetattr(self, name, context=None):
        """infered getattr, need special treatment in class to handle
        descriptors
        """
        # set lookoup name since this is necessary to infer on import nodes for
        # instance
        context = copy_context(context)
        context.lookupname = name
        try:
            for infered in _infer_stmts(self.getattr(name, context), context,
                                        frame=self):
                # yield YES object instead of descriptors when necessary
                if not isinstance(infered, Const) and isinstance(infered, Instance):
                    try:
                        infered._proxied.getattr('__get__', context)
                    except NotFoundError:
                        yield infered
                    else:
                        yield YES
                else:
                    yield infered
        except NotFoundError:
            if not name.startswith('__') and self.has_dynamic_getattr(context):
                # class handle some dynamic attributes, return a YES object
                yield YES
            else:
                raise InferenceError(name)
        
    def has_dynamic_getattr(self, context=None):
        """return True if the class has a custom __getattr__ or
        __getattribute__ method
        """
        # need to explicitly handle optparse.Values (setattr is not detected)
        if self.name == 'Values' and self.root().name == 'optparse':
            return True
        try:
            self.getattr('__getattr__', context)
            return True
        except NotFoundError:
            #if self.newstyle: XXX cause an infinite recursion error
            try:
                getattribute = self.getattr('__getattribute__', context)[0]
                if getattribute.root().name != '__builtin__':
                    # class has a custom __getattribute__ defined
                    return True
            except NotFoundError:
                pass
        return False
    
    def methods(self):
        """return an iterator on all methods defined in the class and
        its ancestors
        """
        done = {}
        for astng in chain(iter((self,)), self.ancestors()):
            for meth in astng.mymethods():
                if done.has_key(meth.name):
                    continue
                done[meth.name] = None
                yield meth
                
    def mymethods(self):
        """return an iterator on all methods defined in the class"""
        for member in self.values():
            if isinstance(member, Function):
                yield member
                
    def interfaces(self, herited=True, handler_func=_iface_hdlr):
        """return an iterator on interfaces implemented by the given
        class node
        """
        # FIXME: what if __implements__ = (MyIFace, MyParent.__implements__)...
        try:
            implements = Instance(self).getattr('__implements__')[0]
        except NotFoundError:
            return
        if not herited and not implements.frame() is self:
            return
        oneinf = False
        for iface in unpack_infer(implements):
            if iface is YES:
                continue
            if handler_func(iface):
                oneinf = True
                yield iface
        if not oneinf:
            raise InferenceError()
##         if hasattr(implements, 'nodes'):
##             implements = implements.nodes
##         else:
##             implements = (implements,)
##         for iface in implements:
##             # let the handler function take care of this....
##             for iface in handler_func(iface):
##                 yield iface

extend_class(Class, ClassNG)
