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

:version:   $Revision: 1.25 $  
:author:    Sylvain Thenault
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2006 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__revision__ = "$Id: inference.py,v 1.25 2006-04-20 07:37:28 syt Exp $"
__doctype__ = "restructuredtext en"

from logilab.common.compat import imap

from logilab.astng import YES, Instance, Generator, \
     unpack_infer, _infer_stmts, nodes
from logilab.astng import InferenceError, UnresolvableName, \
     NoDefault, NotFoundError, ASTNGBuildingException

def path_wrapper(func):
    """return the given infer function wrapped to handle the path"""
    def wrapped(node, name=None, path=None, _func=func, **kwargs):
        """wrapper function handling path"""
        if path is None:
            path = [(node, name)]
        else:
            if (node, name) in path:
                raise StopIteration()
            path.append( (node, name) )
        #print '--'*len(path),_func.__name__[6:], getattr(path[-1][0], 'name', ''), name
        try:
            for res in _func(node, name, path, **kwargs):
                #print '--'*len(path), _func.__name__[6:], '-->', res
                yield res
            path.pop()
        except:
            path.pop()
            raise
    return wrapped

# .infer method ###############################################################

def infer_default(self, name=None, path=None):
    """we don't know how to resolve a statement by default"""
    #print 'inference error', self, name, path
    raise InferenceError(self.__class__.__name__)

#infer_default = infer_default
nodes.Node.infer = infer_default


def infer_end(self, name=None, path=None):
    """inference's end for node such as Module, Class, Function, Const...
    """
    yield self

#infer_end = path_wrapper(infer_end)
nodes.Module.infer = nodes.Class.infer = infer_end
nodes.List.infer = infer_end
nodes.Tuple.infer = infer_end
nodes.Dict.infer = infer_end
nodes.Const.infer = infer_end


def infer_function(self, name=None, path=None):
    """infer on Function nodes must be take with care since it
    may be called to infer one of it's argument (in which case <name>
    should be given)
    """
    # no name is given, we are infering the function itself
    if name is None:
        yield self
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
        for infered in self.default_value(name).infer(name, path):
            yield infered
        yield YES
    except NoDefault:
        yield YES

nodes.Function.infer = path_wrapper(infer_function)
nodes.Lambda.infer = path_wrapper(infer_function)


def infer_name(self, name=None, path=None):
    """infer a Name: use name lookup rules"""
    frame, stmts = self.lookup(self.name)
    if not stmts:
        raise UnresolvableName(name)
    return _infer_stmts(stmts, self.name, path, frame)

nodes.Name.infer = path_wrapper(infer_name)


def infer_assname(self, name=None, path=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = self.assigned_stmts(inf_path=path)
    return _infer_stmts(stmts, self.name, path)
    
nodes.AssName.infer = path_wrapper(infer_assname)


def infer_assattr(self, name=None, path=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = self.assigned_stmts(inf_path=path)
    return _infer_stmts(stmts, self.attrname, path)
    
nodes.AssAttr.infer = path_wrapper(infer_assattr)


def infer_callfunc(self, name=None, path=None):
    """infer a CallFunc node by trying to guess what's the function is
    returning
    """
    one_infered = False
    for callee in self.node.infer(name, path):
        if callee is YES:
            yield callee
            one_infered = True
            continue
        try:
            for infered in callee.infer_call_result(self, path):
                yield infered
                one_infered = True
        except (AttributeError, InferenceError):
            ## XXX log error ?
            continue
    if not one_infered:
        raise InferenceError()

nodes.CallFunc.infer = path_wrapper(infer_callfunc)


def infer_getattr(self, name=None, path=None):
    """infer a Getattr node by using getattr on the associated object
    """
    one_infered = False    
    for owner in self.expr.infer(name, path):
        if owner is YES:
            yield owner
            one_infered = True
            continue
        try:
            for obj in owner.igetattr(self.attrname, path=path):
                yield obj
                one_infered = True
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
        
def infer_import(self, name, path=None, asname=True):
    """self resolve on From / Import nodes return the imported module/object"""
    if name is None:
        infer_default(self, name, path)
    if asname:
        yield _imported_module_astng(self, self.real_name(name))
    else:
        yield _imported_module_astng(self, name)
    
nodes.Import.infer = path_wrapper(infer_import)

def infer_from(self, name, path=None, asname=True):
    """self resolve on From / Import nodes return the imported module/object"""
    if name is None:
        infer_default(self, name, path)
    module = _imported_module_astng(self, self.modname)
    if asname:
        name = self.real_name(name)
    try:
        return _infer_stmts(module.getattr(name), name, path)
    except NotFoundError:
        raise InferenceError(name)

nodes.From.infer = path_wrapper(infer_from)


def infer_global(self, name=None, path=None):
    try:
        return _infer_stmts(self.root().getattr(name), name, path)
    except NotFoundError:
        raise InferenceError()
nodes.Global.infer = path_wrapper(infer_global)

# .infer_call_result method ###################################################
def callable_default(self):
    return False
nodes.Node.callable = callable_default
def callable_true(self):
    return True
nodes.Function.callable = callable_true
nodes.Lambda.callable = callable_true
nodes.Class.callable = callable_true

def infer_call_result_function(self, caller, inf_path=None):
    """infer what's a function is returning wen called"""
    if self.is_generator():
        yield Generator(self)
        return
    returns = self.nodes_of_class(nodes.Return, skip_klass=nodes.Function)
    #for infered in _infer_stmts(imap(lambda n:n.value, returns), path=inf_path):
    #    yield infered
    for returnnode in returns:
        try:
            for infered in returnnode.value.infer(path=inf_path):
                yield infered
        except InferenceError:
            yield YES
nodes.Function.infer_call_result = infer_call_result_function

def infer_call_result_class(self, caller, inf_path=None):
    """infer what's a class is returning when called"""
    yield Instance(self)

nodes.Class.infer_call_result = infer_call_result_class


# Assignment related nodes ####################################################

def assend_assigned_stmts(self, inf_path=None):
    # only infer *real* assignments
    if self.flags == 'OP_DELETE':
        raise InferenceError()
    return self.parent.assigned_stmts(self, inf_path=inf_path)
    
nodes.AssName.assigned_stmts = assend_assigned_stmts
nodes.AssAttr.assigned_stmts = assend_assigned_stmts

def mulass_assigned_stmts(self, node, path=None, inf_path=None):
    if path is None:
        path = []
    node_idx = self.nodes.index(node)
    path.insert(0, node_idx)
    return self.parent.assigned_stmts(self, path, inf_path)
nodes.AssTuple.assigned_stmts = mulass_assigned_stmts
nodes.AssList.assigned_stmts = mulass_assigned_stmts

def assign_assigned_stmts(self, node, path=None, inf_path=None):
    """WARNING here `path` is a list of index to follow"""
    if not path:
        yield self.expr 
        return
    found = False
    for infered in _resolve_asspart(self.expr.infer(path=inf_path), path, inf_path):
        found = True
        yield infered
    if not found:
        raise InferenceError()

nodes.Assign.assigned_stmts = assign_assigned_stmts

def _resolve_asspart(parts, asspath, path):
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
                for infered in _resolve_asspart(assigned.infer(path=path), asspath, path):
                    yield infered
            except InferenceError:
                return
    
def tryexcept_assigned_stmts(self, node, path=None, inf_path=None):
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
    
def XXX_assigned_stmts(self, node, path=None, inf_path=None):
    raise InferenceError()
nodes.For.assigned_stmts = XXX_assigned_stmts
nodes.ListCompFor.assigned_stmts = XXX_assigned_stmts
nodes.GenExprFor.assigned_stmts = XXX_assigned_stmts

def end_ass_type(self):
    return self
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
def assend_ass_type(self, inf_path=None):
    # only infer *real* assignments
    if self.flags == 'OP_DELETE':
        return self
    return self.parent.ass_type()
nodes.AssName.ass_type = assend_ass_type
nodes.AssAttr.ass_type = assend_ass_type

# subscription protocol #######################################################
        
def getitem(self, index):
    return self.nodes[index]
nodes.List.getitem = getitem
nodes.Tuple.getitem = getitem
#Dict.getitem = getitem XXX

