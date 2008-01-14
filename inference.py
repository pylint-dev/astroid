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
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__doctype__ = "restructuredtext en"

from copy import copy

from logilab.common.compat import imap, chain, set

from logilab.astng import MANAGER, YES, InferenceContext, Instance, Generator, \
     unpack_infer, _infer_stmts, nodes, copy_context
from logilab.astng import ASTNGError, InferenceError, UnresolvableName, \
     NoDefault, NotFoundError, ASTNGBuildingException

    
def path_wrapper(func):
    """return the given infer function wrapped to handle the path"""
    def wrapped(node, context=None, _func=func, **kwargs):
        """wrapper function handling context"""
        if context is None:
            context = InferenceContext(node)
        context.push(node)
        yielded = set()
        try:
            for res in _func(node, context, **kwargs):
                # unproxy only true instance, not const, tuple, dict...
                if res.__class__ is Instance:
                    ares = res._proxied
                else:
                    ares = res
                if not ares in yielded:
                    yield res
                    yielded.add(ares)
            context.pop()
        except:
            context.pop()
            raise
    return wrapped

# .infer method ###############################################################

def infer_default(self, context=None):
    """we don't know how to resolve a statement by default"""
    #print 'inference error', self, name, path
    raise InferenceError(self.__class__.__name__)

#infer_default = infer_default
nodes.Node.infer = infer_default


def infer_end(self, context=None):
    """inference's end for node such as Module, Class, Function, Const...
    """
    yield self

#infer_end = path_wrapper(infer_end)
nodes.Module.infer = nodes.Class.infer = infer_end
nodes.List.infer = infer_end
nodes.Tuple.infer = infer_end
nodes.Dict.infer = infer_end
nodes.Const.infer = infer_end

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
    


class CallContext:
    """when infering a function call, this class is used to remember values
    given as argument
    """
    def __init__(self, args, starargs, dstarargs):
        self.args = []
        self.nargs = {}
        for arg in args:
            if isinstance(arg, nodes.Keyword):
                self.nargs[arg.name] = arg.expr
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
            # Function.argnames can be None in astng (means that we don't have
            # information on argnames)
            if funcnode.argnames is not None:
                try:
                    argindex = funcnode.argnames.index(name)
                except ValueError:
                    pass
                else:
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
        mularg = funcnode.mularg_class(name)
        if mularg is not None: 
            # XXX should be able to compute values inside
            return iter((mularg,))
        # 6. return default value if any
        try:
            return funcnode.default_value(name).infer(context)
        except NoDefault:
            raise InferenceError(name)
        
        
def infer_function(self, context=None):
    """infer on Function nodes must be take with care since it
    may be called to infer one of it's argument (in which case <name>
    should be given)
    """
    name = context.lookupname
    # no name is given, we are infering the function itself
    if name is None:
        yield self
        return
    if context.callcontext:
        # reset call context/name
        callcontext = context.callcontext
        context = copy_context(context)
        context.callcontext = None
        for infered in callcontext.infer_argument(self, name, context):
            yield infered
        return
    # Function.argnames can be None in astng (means that we don't have
    # information on argnames), in which case we can't do anything more
    if self.argnames is None:
        yield YES
        return
    if not name in self.argnames:
        raise InferenceError()
    # first argument of instance/class method
    if name == self.argnames[0]:
        if self.type == 'method':
            yield Instance(self.parent.frame())
            return
        if self.type == 'classmethod':
            yield self.parent.frame()
            return
    mularg = self.mularg_class(name)
    if mularg is not None: # */** argument, no doubt it's a Tuple or Dict
        yield mularg
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

nodes.Function.infer = path_wrapper(infer_function)
nodes.Lambda.infer = path_wrapper(infer_function)


def infer_name(self, context=None):
    """infer a Name: use name lookup rules"""
    context = context.clone()
    context.lookupname = self.name
    frame, stmts = self.lookup(self.name)
    if not stmts:
        raise UnresolvableName(self.name)
    return _infer_stmts(stmts, context, frame)

nodes.Name.infer = path_wrapper(infer_name)


def infer_assname(self, context=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = self.assigned_stmts(context=context)
    return _infer_stmts(stmts, context)
    
nodes.AssName.infer = path_wrapper(infer_assname)


def infer_assattr(self, context=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = self.assigned_stmts(context=context)
    return _infer_stmts(stmts, context)
    
nodes.AssAttr.infer = path_wrapper(infer_assattr)

        
def infer_callfunc(self, context=None):
    """infer a CallFunc node by trying to guess what's the function is
    returning
    """
    one_infered = False
    context = context.clone()
    context.callcontext = CallContext(self.args, self.star_args, self.dstar_args)
    for callee in self.node.infer(context):
        if callee is YES:
            yield callee
            one_infered = True
            continue
        try:
            for infered in callee.infer_call_result(self, context):
                yield infered
                one_infered = True
        except (AttributeError, InferenceError):
            ## XXX log error ?
            continue
    if not one_infered:
        raise InferenceError()

nodes.CallFunc.infer = path_wrapper(infer_callfunc)


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
    """self resolve on From / Import nodes return the imported module/object"""
    name = context.lookupname
    if name is None:
        raise InferenceError()
    if asname:
        yield _imported_module_astng(self, self.real_name(name))
    else:
        yield _imported_module_astng(self, name)
    
nodes.Import.infer = path_wrapper(infer_import)

def infer_from(self, context=None, asname=True):
    """self resolve on From / Import nodes return the imported module/object"""
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

def infer_unarysub(self, context=None):
    for infered in self.expr.infer(context):
        try:
            value = -infered.value
        except (TypeError, AttributeError):
            yield YES
            continue
        node = copy(self.expr)
        node.value = value
        yield node
nodes.UnarySub.infer = path_wrapper(infer_unarysub)

def infer_unaryadd(self, context=None):
    return self.expr.infer(context)
nodes.UnaryAdd.infer = infer_unaryadd

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

def _infer_operator(self, context=None, impl=None, meth='__method__'):
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
            if type(value) is type(lhsvalue):
                node = copy(lhs)
            else:
                node = copy(rhs)
            # XXX may be dict, tuple...
            node.value = value
            yield node

def infer_sub(self, context=None):
    return _infer_operator(self, context=context, impl=lambda a,b: a-b, meth='__sub__')
nodes.Sub.infer = path_wrapper(infer_sub)

def infer_add(self, context=None):
    return _infer_operator(self, context=context, impl=lambda a,b: a+b, meth='__add__')
nodes.Add.infer = path_wrapper(infer_add)

def infer_mul(self, context=None):
    return _infer_operator(self, context=context, impl=lambda a,b: a*b, meth='__mul__')
nodes.Mul.infer = path_wrapper(infer_mul)

def infer_div(self, context=None):
    return _infer_operator(self, context=context, impl=lambda a,b: a/b, meth='__div__')
nodes.Div.infer = path_wrapper(infer_div)
    
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
    """infer what's a function is returning when called"""
    if self.is_generator():
        yield Generator(self)
        return
    returns = self.nodes_of_class(nodes.Return, skip_klass=nodes.Function)
    for returnnode in returns:
        try:
            for infered in returnnode.value.infer(context):
                yield infered
        except InferenceError:
            yield YES
nodes.Function.infer_call_result = infer_call_result_function

def infer_call_result_lambda(self, caller, context=None):
    """infer what's a function is returning when called"""
    return self.code.infer(context)
nodes.Lambda.infer_call_result = infer_call_result_lambda

def infer_call_result_class(self, caller, context=None):
    """infer what's a class is returning when called"""
    yield Instance(self)

nodes.Class.infer_call_result = infer_call_result_class


# Assignment related nodes ####################################################
"""the assigned_stmts method is responsible to return the assigned statement
(eg not infered) according to the assignment type.

The `asspath` argument is used to record the lhs path of the original node.
For instance if we want assigned statements for 'c' in 'a, (b,c)', asspath
will be [1, 1] once arrived to the Assign node.

The `context` argument is the current inference context which should be given
to any intermediary inference necessary.
"""
def assend_assigned_stmts(self, context=None):
    # only infer *real* assignments
    if self.flags == 'OP_DELETE':
        raise InferenceError()
    return self.parent.assigned_stmts(self, context=context)
    
nodes.AssName.assigned_stmts = assend_assigned_stmts
nodes.AssAttr.assigned_stmts = assend_assigned_stmts

def mulass_assigned_stmts(self, node, context=None, asspath=None):
    if asspath is None:
        asspath = []
    node_idx = self.nodes.index(node)
    asspath.insert(0, node_idx)
    return self.parent.assigned_stmts(self, context, asspath)
nodes.AssTuple.assigned_stmts = mulass_assigned_stmts
nodes.AssList.assigned_stmts = mulass_assigned_stmts

def assign_assigned_stmts(self, node, context=None, asspath=None):
    if not asspath:
        yield self.expr 
        return
    found = False
    for infered in _resolve_asspart(self.expr.infer(context), asspath, context):
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
        try:
            assigned = part.getitem(index)
        except (AttributeError, IndexError):
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
                for infered in _resolve_asspart(assigned.infer(context), asspath, context):
                    yield infered
            except InferenceError:
                return
    
def tryexcept_assigned_stmts(self, node, context=None, asspath=None):
    found = False
    for exc_type, exc_obj, body in self.handlers:
        if node is exc_obj:
            for assigned in unpack_infer(exc_type):
                if isinstance(assigned, nodes.Class):
                    assigned = Instance(assigned)
                yield assigned
                found = True
            break
    if not found:
        raise InferenceError()
nodes.TryExcept.assigned_stmts = tryexcept_assigned_stmts


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
        for lst in self.loop_node().infer(context):
            if isinstance(lst, (nodes.Tuple, nodes.List)):
                for item in lst.nodes:
                    found = True
                    yield item
    else:
        for infered in _resolve_looppart(self.loop_node().infer(context), asspath, context):
            found = True
            yield infered
    if not found:
        raise InferenceError()
nodes.For.assigned_stmts = for_assigned_stmts
nodes.ListCompFor.assigned_stmts = for_assigned_stmts
nodes.GenExprFor.assigned_stmts = for_assigned_stmts

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

    
def end_ass_type(self):
    return self
nodes.With.ass_type = end_ass_type
nodes.For.ass_type = end_ass_type
nodes.ListCompFor.ass_type = end_ass_type
nodes.GenExprFor.ass_type = end_ass_type
nodes.TryExcept.ass_type = end_ass_type
nodes.Assign.ass_type = end_ass_type
nodes.AugAssign.ass_type = end_ass_type
def parent_ass_type(self):
    return self.parent.ass_type()
nodes.AssName.ass_type = parent_ass_type
nodes.AssAttr.ass_type = parent_ass_type
nodes.AssTuple.ass_type = parent_ass_type
nodes.AssList.ass_type = parent_ass_type
def assend_ass_type(self, context=None):
    # only infer *real* assignments
    if self.flags == 'OP_DELETE':
        return self
    return self.parent.ass_type()
nodes.AssName.ass_type = assend_ass_type
nodes.AssAttr.ass_type = assend_ass_type

# subscription protocol #######################################################
        
def tl_getitem(self, index):
    return self.nodes[index]
nodes.List.getitem = tl_getitem
nodes.Tuple.getitem = tl_getitem
        
def tl_iter_stmts(self):
    return self.nodes
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


def for_loop_node(self):
    return self.list
nodes.For.loop_node = for_loop_node
nodes.ListCompFor.loop_node = for_loop_node

def gen_loop_nodes(self):
    return self.iter
nodes.GenExprFor.loop_node = gen_loop_nodes
