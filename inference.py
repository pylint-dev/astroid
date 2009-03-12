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
"""this module contains a set of functions to handle inference on astng trees

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__doctype__ = "restructuredtext en"

from copy import copy

from logilab.common.compat import imap, chain, set

from logilab.astng import nodes, MANAGER, \
     unpack_infer, copy_context, path_wrapper
from logilab.astng import ASTNGError, InferenceError, UnresolvableName, \
     NoDefault, NotFoundError, ASTNGBuildingException
from logilab.astng.nodes import _infer_stmts, YES, InferenceContext, Instance, \
     Generator
     

def infer_end(self, context=None):
    """inference's end for node such as Module, Class, Function, Const...
    """
    yield self
    
    
nodes.List._proxied = MANAGER.astng_from_class(list)
nodes.List.__bases__ += (Instance,)
nodes.List.pytype = lambda x: '__builtin__.list'
nodes.Tuple._proxied = MANAGER.astng_from_class(tuple)
nodes.Tuple.__bases__ += (Instance,)
nodes.Tuple.pytype = lambda x: '__builtin__.tuple'
nodes.Dict.__bases__ += (Instance,)
nodes.Dict._proxied = MANAGER.astng_from_class(dict)
nodes.Dict.pytype = lambda x: '__builtin__.dict'
# nodes.NoneType.pytype = lambda x: 'types.NoneType'
# nodes.Bool._proxied = MANAGER.astng_from_class(bool)

builtin_astng = nodes.Dict._proxied.root()

# .infer method ###############################################################

def infer_default(self, context=None):
    """we don't know how to resolve a statement by default"""
    raise InferenceError(self.__class__.__name__)

nodes.Node.infer = infer_default

#infer_end = path_wrapper(infer_end)
nodes.Module.infer = nodes.Class.infer = infer_end        
nodes.Function.infer = infer_end
nodes.Lambda.infer = infer_end
nodes.List.infer = infer_end
nodes.Tuple.infer = infer_end
nodes.Dict.infer = infer_end


class CallContext:
    """when infering a function call, this class is used to remember values
    given as argument
    """
    def __init__(self, args, starargs, dstarargs):
        self.args = []
        self.nargs = {}
        for arg in args:
            if isinstance(arg, nodes.Keyword):
                self.nargs[arg.arg] = arg.value
            else:
                self.args.append(arg)
        self.starargs = starargs
        self.dstarargs = dstarargs

    def infer_argument(self, funcnode, name, context):
        """infer a function argument value according the the call context"""
        # 1. search in named keywords
        try:
            return self.nargs[name].infer(context)
        except KeyError:
            # Function.args.args can be None in astng (means that we don't have
            # information on argnames)
            argindex, argnode = funcnode.args.find_argname(name)
            if argindex is not None:
                # 2. first argument of instance/class method
                if argindex == 0 and funcnode.type in ('method', 'classmethod'):
                    if context.boundnode is not None:
                        boundnode = context.boundnode
                    else:
                        # XXX can do better ?
                        boundnode = funcnode.parent.frame()
                    if funcnode.type == 'method':
                        return iter((Instance(boundnode),))
                    if funcnode.type == 'classmethod':
                        return iter((boundnode,))                            
                # 2. search arg index
                try:
                    return self.args[argindex].infer(context)
                except IndexError:
                    pass
                # 3. search in *args (.starargs)
                if self.starargs is not None:
                    its = []
                    for infered in self.starargs.infer(context):
                        if infered is YES:
                            its.append((YES,))
                            continue
                        try:
                            its.append(infered.getitem(argindex).infer(context))
                        except (InferenceError, AttributeError):
                            its.append((YES,))
                        except IndexError:
                            continue
                    if its:
                        return chain(*its)
        # 4. XXX search in **kwargs (.dstarargs)
        if self.dstarargs is not None:
            its = []
            for infered in self.dstarargs.infer(context):
                if infered is YES:
                    its.append((YES,))
                    continue
                try:
                    its.append(infered.getitem(name).infer(context))
                except (InferenceError, AttributeError):
                    its.append((YES,))
                except IndexError:
                    continue
            if its:
                return chain(*its)
        # 5. */** argument, (Tuple or Dict)
        if name == funcnode.args.vararg:
            return iter((nodes.Tuple(),))
        if name == funcnode.args.kwarg:
            return iter((nodes.Dict(),))
        # 6. return default value if any
        try:
            return funcnode.args.default_value(name).infer(context)
        except NoDefault:
            raise InferenceError(name)
        


def infer_name(self, context=None):
    """infer a Name: use name lookup rules"""
    frame, stmts = self.lookup(self.name)
    if not stmts:
        raise UnresolvableName(self.name)
    context = context.clone()
    context.lookupname = self.name
    return _infer_stmts(stmts, context, frame)

nodes.Name.infer = path_wrapper(infer_name)

        
def infer_callfunc(self, context=None):
    """infer a CallFunc node by trying to guess what the function returns
    """
    one_infered = False
    context = context.clone()
    context.callcontext = CallContext(self.args, self.starargs, self.kwargs)
    for callee in self.func.infer(context):
        if callee is YES:
            yield callee
            one_infered = True
            continue
        try:
            if hasattr(callee, 'infer_call_result'):
                for infered in callee.infer_call_result(self, context):
                    yield infered
                    one_infered = True
        except InferenceError:
            ## XXX log error ?
            continue
    if not one_infered:
        raise InferenceError()

nodes.CallFunc.infer = path_wrapper(infer_callfunc)


def _imported_module_astng(node, modname):
    """return the ast for a module whose name is <modname> imported by <node>
    """
    # handle special case where we are on a package node importing a module
    # using the same name as the package, which may end in an infinite loop
    # on relative imports
    # XXX: no more needed ?
    mymodule = node.root()
    if mymodule.relative_name(modname) == mymodule.name:
        # FIXME: I don't know what to do here...
        raise InferenceError(modname)
    try:
        return mymodule.import_module(modname)
    except (ASTNGBuildingException, SyntaxError):
        raise InferenceError(modname)
        
def infer_import(self, context=None, asname=True):
    """infer an Import node: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise InferenceError()
    if asname:
        yield _imported_module_astng(self, self.real_name(name))
    else:
        yield _imported_module_astng(self, name)
    
nodes.Import.infer = path_wrapper(infer_import)

def infer_from(self, context=None, asname=True):
    """infer a From nodes: return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise InferenceError()
    if asname:
        name = self.real_name(name)
    module = _imported_module_astng(self, self.modname)
    try:
        context = copy_context(context)
        context.lookupname = name
        return _infer_stmts(module.getattr(name), context)
    except NotFoundError:
        raise InferenceError(name)

nodes.From.infer = path_wrapper(infer_from)
    

def infer_getattr(self, context=None):
    """infer a Getattr node by using getattr on the associated object
    """
    one_infered = False
    # XXX
    #context = context.clone()
    for owner in self.expr.infer(context):
        if owner is YES:
            yield owner
            one_infered = True
            continue
        try:
            context.boundnode = owner
            for obj in owner.igetattr(self.attrname, context):
                yield obj
                one_infered = True
            context.boundnode = None
        except (NotFoundError, InferenceError):
            continue
        except AttributeError:
            # XXX method / function
            continue
    if not one_infered:
        raise InferenceError()
nodes.Getattr.infer = path_wrapper(infer_getattr)


def infer_global(self, context=None):
    if context.lookupname is None:
        raise InferenceError()
    try:
        return _infer_stmts(self.root().getattr(context.lookupname), context)
    except NotFoundError:
        raise InferenceError()
nodes.Global.infer = path_wrapper(infer_global)


def infer_subscript(self, context=None):
    """infer simple subscription such as [1,2,3][0] or (1,2,3)[-1]
    """
    if len(self.subs) == 1:
        index = self.subs[0].infer(context).next()
        if index is YES:
            yield YES
            return
        try:
            # suppose it's a Tuple/List node (attribute error else)
            assigned = self.expr.getitem(index.value)
        except AttributeError:
            raise InferenceError()
        except IndexError:
            yield YES
            return
        for infered in assigned.infer(context):
            yield infered
    else:
        raise InferenceError()
nodes.Subscript.infer = path_wrapper(infer_subscript)

# def infer_unarysub(self, context=None):
#     for infered in self.expr.infer(context):
#         try:
#             value = -infered.value
#         except (TypeError, AttributeError):
#             yield YES
#             continue
#         node = copy(self.expr)
#         node.value = value
#         yield node
# nodes.UnarySub.infer = path_wrapper(infer_unarysub)

# def infer_unaryadd(self, context=None):
#     return self.expr.infer(context)
# nodes.UnaryAdd.infer = infer_unaryadd

def _py_value(node):
    try:
        return node.value
    except AttributeError:
        # not a constant
        if isinstance(node, nodes.Dict):
            return {}
        if isinstance(node, nodes.List):
            return []
        if isinstance(node, nodes.Tuple):
            return ()
    raise ValueError()

def _infer_unary_operator(self, context=None, impl=None, meth=None):
    for operand in self.operand.infer(context):
        try:
            value = _py_value(operand)
        except ValueError:
            # not a constant
            if meth is None:
                yield YES
                continue
            try:
                # XXX just suppose if the type implement meth, returned type
                # will be the same
                operand.getattr(meth)
                yield operand
            except GeneratorExit:
                raise
            except:
                yield YES
            continue
        try:
            value = impl(value)
        except: # TypeError:
            yield YES
            continue
        yield nodes.const_factory(value)

UNARY_OP_IMPL = {'+':  (lambda a: +a, '__pos__'),
                 '-':  (lambda a: -a, '__neg__'),
                 'not':  (lambda a: not a, None), # XXX not '__nonzero__'
                 }
def infer_unaryop(self, context=None):
    impl, meth = UNARY_OP_IMPL[self.op]
    return _infer_unary_operator(self, context=context, impl=impl, meth=meth)
nodes.UnaryOp.infer = path_wrapper(infer_unaryop)

def _infer_binary_operator(self, context=None, impl=None, meth='__method__'):
    for lhs in self.left.infer(context):
        try:
            lhsvalue = _py_value(lhs)
        except ValueError:
            # not a constant
            try:
                # XXX just suppose if the type implement meth, returned type
                # will be the same
                lhs.getattr(meth)
                yield lhs
            except:
                yield YES
            continue
        for rhs in self.right.infer(context):
            try:
                rhsvalue = _py_value(rhs)
            except ValueError:
                try:
                    # XXX just suppose if the type implement meth, returned type
                    # will be the same
                    rhs.getattr(meth)
                    yield rhs
                except:
                    yield YES
                continue
            try:
                value = impl(lhsvalue, rhsvalue)
            except TypeError:
                yield YES
                continue
            yield nodes.const_factory(value)

BIN_OP_IMPL = {'+':  (lambda a,b: a+b, '__add__'),
               '-':  (lambda a,b: a-b, '__sub__'),
               '/':  (lambda a,b: a/b, '__div__'),
               '//': (lambda a,b: a//b, '__floordiv__'),
               '*':  (lambda a,b: a*b, '__mul__'),
               '**': (lambda a,b: a**b, '__power__'),
               '%':  (lambda a,b: a%b, '__mod__'),
               '&':  (lambda a,b: a&b, '__and__'),
               '|':  (lambda a,b: a|b, '__or__'),
               '^':  (lambda a,b: a^b, '__xor__'),
               '<<':  (lambda a,b: a^b, '__lshift__'),
               '>>':  (lambda a,b: a^b, '__rshift__'),
               }
def infer_binop(self, context=None):
    impl, meth = BIN_OP_IMPL[self.op]
    return _infer_binary_operator(self, context=context, impl=impl, meth=meth)
nodes.BinOp.infer = path_wrapper(infer_binop)

def infer_arguments(self, context=None):
    name = context.lookupname
    if name is None:
        raise InferenceError()
    return _arguments_infer_argname(self, name, context)
nodes.Arguments.infer = infer_arguments
    
# .infer_call_result method ###################################################
def callable_default(self):
    return False
nodes.Node.callable = callable_default
def callable_true(self):
    return True
nodes.Function.callable = callable_true
nodes.Lambda.callable = callable_true
nodes.Class.callable = callable_true

def infer_call_result_function(self, caller, context=None):
    """infer what a function is returning when called"""
    if self.is_generator():
        yield Generator(self)
        return
    returns = self.nodes_of_class(nodes.Return, skip_klass=nodes.Function)
    for returnnode in returns:
        if returnnode.value is None:
            yield None
        else:
            try:
                for infered in returnnode.value.infer(context):
                    yield infered
            except InferenceError:
                yield YES
nodes.Function.infer_call_result = infer_call_result_function

def infer_call_result_lambda(self, caller, context=None):
    """infer what a function is returning when called"""
    return self.body.infer(context)
nodes.Lambda.infer_call_result = infer_call_result_lambda

def infer_call_result_class(self, caller, context=None):
    """infer what a class is returning when called"""
    yield Instance(self)

nodes.Class.infer_call_result = infer_call_result_class

def infer_empty_node(self, context=None):
    if not self.has_underlying_object():
        yield YES
    else:
        try:
            for infered in MANAGER.infer_astng_from_something(self.object,
                                                              context=context):
                yield infered
        except ASTNGError:
            yield YES
nodes.EmptyNode.infer = path_wrapper(infer_empty_node)


nodes.Const.__bases__ += (Instance,)

from types import NoneType

_CONST_PROXY = {
    NoneType: MANAGER.astng_from_class(NoneType, 'types'),
    bool: MANAGER.astng_from_class(bool),
    int: MANAGER.astng_from_class(int),
    float: MANAGER.astng_from_class(float),
    complex: MANAGER.astng_from_class(complex),
    str: MANAGER.astng_from_class(str),
    unicode: MANAGER.astng_from_class(unicode),
    }

def _set_proxied(const):
    if not hasattr(const, '__proxied'):
        const.__proxied = _CONST_PROXY[const.value.__class__]
    return const.__proxied
nodes.Const._proxied = property(_set_proxied)

def Const_getattr(self, name, context=None, lookupclass=None):
    return self._proxied.getattr(name, context)
nodes.Const.getattr = Const_getattr
nodes.Const.has_dynamic_getattr = lambda x: False

def Const_pytype(self):
    return self._proxied.qname()
nodes.Const.pytype = Const_pytype

nodes.Const.infer = infer_end


# Assignment related nodes ####################################################
"""the assigned_stmts method is responsible to return the assigned statement
(eg not infered) according to the assignment type.

The `asspath` argument is used to record the lhs path of the original node.
For instance if we want assigned statements for 'c' in 'a, (b,c)', asspath
will be [1, 1] once arrived to the Assign node.

The `context` argument is the current inference context which should be given
to any intermediary inference necessary.
"""

def infer_ass(self, context=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = list(self.assigned_stmts(context=context))
    return nodes._infer_stmts(stmts, context)
nodes.AssName.infer = path_wrapper(infer_ass)
nodes.AssAttr.infer = path_wrapper(infer_ass)
# no infer method on DelName and DelAttr (expected InferenceError)

def _resolve_looppart(parts, asspath, context):
    """recursive function to resolve multiple assignments on loops"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if part is YES:
            continue
        if not hasattr(part, 'iter_stmts'):
            continue
        for stmt in part.iter_stmts():
            try:
                assigned = stmt.getitem(index)
            except (AttributeError, IndexError):
                continue
            if not asspath:
                # we acheived to resolved the assigment path,
                # don't infer the last part
                found = True
                yield assigned
            elif assigned is YES:
                break
            else:
                # we are not yet on the last part of the path
                # search on each possibly infered value
                try:
                    for infered in _resolve_looppart(assigned.infer(context), asspath, context):
                        yield infered
                except InferenceError:
                    break

def for_assigned_stmts(self, node, context=None, asspath=None):
    found = False
    if asspath is None:
        for lst in self.iter.infer(context):
            if isinstance(lst, (nodes.Tuple, nodes.List)):
                for item in lst.elts:
                    found = True
                    yield item
    else:
        for infered in _resolve_looppart(self.iter.infer(context), asspath, context):
            found = True
            yield infered
    if not found:
        raise InferenceError()
nodes.For.assigned_stmts = for_assigned_stmts
nodes.Comprehension.assigned_stmts = for_assigned_stmts


def mulass_assigned_stmts(self, node, context=None, asspath=None):
    if asspath is None:
        asspath = []
    asspath.insert(0, self.elts.index(node))
    return self.parent.assigned_stmts(self, context, asspath)
nodes.Tuple.assigned_stmts = mulass_assigned_stmts
nodes.List.assigned_stmts = mulass_assigned_stmts


def assend_assigned_stmts(self, context=None):
    return self.parent.assigned_stmts(self, context=context)    
nodes.AssName.assigned_stmts = assend_assigned_stmts
nodes.AssAttr.assigned_stmts = assend_assigned_stmts

def arguments_assigned_stmts(self, node, context, asspath=None):
    if context.callcontext:
        # reset call context/name
        callcontext = context.callcontext
        context = copy_context(context)
        context.callcontext = None
        for infered in callcontext.infer_argument(self.parent, node.name, context):
            yield infered
        return
    for infered in _arguments_infer_argname(self, node.name, context):
        yield infered
        
nodes.Arguments.assigned_stmts = arguments_assigned_stmts

def _arguments_infer_argname(self, name, context):
    # arguments informmtion may be missing, in which case we can't do anything
    # more
    if not (self.args or self.vararg or self.kwarg):
        yield YES
        return
    # first argument of instance/class method
    if name == getattr(self.args[0], 'name', None):
        functype = self.parent.type
        if functype == 'method':
            yield Instance(self.parent.parent.frame())
            return
        if functype == 'classmethod':
            yield self.parent.parent.frame()
            return
    if name == self.vararg:
        yield nodes.Tuple()
        return
    if name == self.kwarg:
        yield nodes.Dict()
        return
    # if there is a default value, yield it. And then yield YES to reflect
    # we can't guess given argument value
    try:
        context = copy_context(context)
        for infered in self.default_value(name).infer(context):
            yield infered
        yield YES
    except NoDefault:
        yield YES
        

def assign_assigned_stmts(self, node, context=None, asspath=None):
    if not asspath:
        yield self.value
        return
    found = False
    for infered in _resolve_asspart(self.value.infer(context), asspath, context):
        found = True
        yield infered
    if not found:
        raise InferenceError()
nodes.Assign.assigned_stmts = assign_assigned_stmts

def _resolve_asspart(parts, asspath, context):
    """recursive function to resolve multiple assignments"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if hasattr(part, 'getitem'):
            try:
                assigned = part.getitem(index)
            except IndexError:# XXX getitem could raise a specific exception to avoid potential hiding of unexpected exception
                return
            if not asspath:
                # we acheived to resolved the assigment path,
                # don't infer the last part
                found = True
                yield assigned
            elif assigned is YES:
                return
            else:
                # we are not yet on the last part of the path
                # search on each possibly infered value
                try:
                    for infered in _resolve_asspart(assigned.infer(context), 
                                                    asspath, context):
                        yield infered
                except InferenceError:
                    return
    
def excepthandler_assigned_stmts(self, node, context=None, asspath=None):
    found = False
    for assigned in unpack_infer(self.type):
        if isinstance(assigned, nodes.Class):
            assigned = Instance(assigned)
        yield assigned
        found = True
    if not found:
        raise InferenceError()
nodes.ExceptHandler.assigned_stmts = excepthandler_assigned_stmts



def with_assigned_stmts(self, node, context=None, asspath=None):
    found = False
    if asspath is None:
        for lst in self.vars.infer(context):
            if isinstance(lst, (nodes.Tuple, nodes.List)):
                for item in lst.nodes:
                    found = True
                    yield item
    else:
        raise InferenceError()
    if not found:
        raise InferenceError()
nodes.With.assigned_stmts = with_assigned_stmts



def parent_ass_type(self, context=None):
    return self.parent.ass_type()
    
nodes.Tuple.ass_type = parent_ass_type
nodes.List.ass_type = parent_ass_type
nodes.AssName.ass_type = parent_ass_type
nodes.AssAttr.ass_type = parent_ass_type
nodes.DelName.ass_type = parent_ass_type
nodes.DelAttr.ass_type = parent_ass_type

def end_ass_type(self):
    return self

# XXX if you add ass_type to a class, you should probably modify lookup.filter_stmts around line ::
# if ass_type is mystmt and not isinstance(ass_type, (nodes.Class, nodes.Function, nodes.Import, nodes.From, nodes.Lambda)):
nodes.Arguments.ass_type = end_ass_type
nodes.Assign.ass_type = end_ass_type
nodes.AugAssign.ass_type = end_ass_type
nodes.Class.ass_type = end_ass_type
nodes.Comprehension.ass_type = end_ass_type
nodes.Delete.ass_type = end_ass_type
nodes.ExceptHandler.ass_type = end_ass_type
nodes.For.ass_type = end_ass_type
nodes.From.ass_type = end_ass_type
nodes.Function.ass_type = end_ass_type
nodes.Import.ass_type = end_ass_type
nodes.With.ass_type = end_ass_type

# subscription protocol #######################################################
        
def tl_getitem(self, index):
    return self.elts[index]
nodes.List.getitem = tl_getitem
nodes.Tuple.getitem = tl_getitem
        
def tl_iter_stmts(self):
    return self.elts
nodes.List.iter_stmts = tl_iter_stmts
nodes.Tuple.iter_stmts = tl_iter_stmts

#Dict.getitem = getitem XXX
        
def dict_getitem(self, key):
    for i in xrange(0, len(self.items), 2):
        for inferedkey in self.items[i].infer():
            if inferedkey is YES:
                continue
            if inferedkey.eq(key):
                return self.items[i+1]
    raise IndexError(key)

nodes.Dict.getitem = dict_getitem
        
def dict_iter_stmts(self):
    return self.items[::2]
nodes.Dict.iter_stmts = dict_iter_stmts

