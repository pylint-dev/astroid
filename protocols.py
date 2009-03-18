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
"""this module contains a set of functions to handle python protocols for nodes
where it makes sense.

:author:    Sylvain Thenault
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2009 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from __future__ import generators

__doctype__ = "restructuredtext en"

from logilab.astng import InferenceError, NoDefault, nodes
from logilab.astng.infutils import copy_context, unpack_infer, \
     raise_if_nothing_infered, yes_if_nothing_infered, Instance, Generator, YES
from logilab.astng.nodes import Const, Class, Function, Tuple, List, \
     const_factory

# unary operations ############################################################

def tl_infer_unary_op(self, operator):
    if operator == 'not':
        return const_factory(not bool(self.elts))
    raise TypeError() # XXX log unsupported operation
nodes.Tuple.infer_unary_op = tl_infer_unary_op
nodes.List.infer_unary_op = tl_infer_unary_op


def dict_infer_unary_op(self, operator):
    if operator == 'not':
        return const_factory(not bool(self.items))
    raise TypeError() # XXX log unsupported operation
nodes.Dict.infer_unary_op = dict_infer_unary_op


def const_infer_unary_op(self, operator):
    if operator == 'not':
        return const_factory(not self.value)
    # XXX log potentialy raised TypeError
    elif operator == '+':
        return const_factory(+self.value)
    else: # operator == '-':
        return const_factory(-self.value)        
nodes.Const.infer_unary_op = const_infer_unary_op


# binary operations ###########################################################

BIN_OP_IMPL = {'+':  lambda a, b: a + b,
               '-':  lambda a, b: a - b,
               '/':  lambda a, b: a / b,
               '//': lambda a, b: a // b,
               '*':  lambda a, b: a * b,
               '**': lambda a, b: a ** b,
               '%':  lambda a, b: a % b,
               '&':  lambda a, b: a & b,
               '|':  lambda a, b: a | b,
               '^':  lambda a, b: a ^ b,
               '<<': lambda a, b: a ^ b,
               '>>': lambda a, b: a ^ b,
               }

def const_infer_binary_op(self, operator, other, context):
    for other in other.infer(context):
        if isinstance(other, Const):
            try:
                impl = BIN_OP_IMPL[operator]
                yield const_factory(impl(self.value, other.value))
            except TypeError:
                # XXX log TypeError
                continue
        elif other is YES:
            yield other
        else:
            try:
                for val in other.infer_binary_op(operator, self, context):
                    yield val
            except AttributeError:
                yield YES
nodes.Const.infer_binary_op = yes_if_nothing_infered(const_infer_binary_op)

    
def tl_infer_binary_op(self, operator, other, context):
    for other in other.infer(context):
        if isinstance(other, self.__class__) and operator == '+':
            node = self.__class__()
            elts = [n for elt in self.elts for n in elt.infer(context)]
            elts += [n for elt in other.elts for n in elt.infer(context)]
            node.elts = elts
            yield node
        elif isinstance(other, Const) and operator == '*':
            node = self.__class__()
            elts = [n for elt in self.elts for n in elt.infer(context)] * other.value
            node.elts = elts
            yield node
        elif isinstance(other, Instance) and not isinstance(other, Const):
            yield YES
    # XXX else log TypeError
nodes.Tuple.infer_binary_op = yes_if_nothing_infered(tl_infer_binary_op)
nodes.List.infer_binary_op = yes_if_nothing_infered(tl_infer_binary_op)


def dict_infer_binary_op(self, operator, other, context):
    for other in other.infer(context):
        if isinstance(other, Instance) and isinstance(other._proxied, Class):
            yield YES
        # XXX else log TypeError
nodes.Dict.infer_binary_op = yes_if_nothing_infered(dict_infer_binary_op)


# assignment ##################################################################

"""the assigned_stmts method is responsible to return the assigned statement
(eg not infered) according to the assignment type.

The `asspath` argument is used to record the lhs path of the original node.
For instance if we want assigned statements for 'c' in 'a, (b,c)', asspath
will be [1, 1] once arrived to the Assign node.

The `context` argument is the current inference context which should be given
to any intermediary inference necessary.
"""

def _resolve_looppart(parts, asspath, context):
    """recursive function to resolve multiple assignments on loops"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if part is YES:
            continue
        # XXX handle __iter__ and log potentially detected errors
        if not hasattr(part, 'itered'):
            continue
        try:
            itered = part.itered()
        except TypeError:
            continue # XXX log error
        for stmt in itered:
            try:
                assigned = stmt.getitem(index, context)
            except (AttributeError, IndexError):
                continue
            if not asspath:
                # we acheived to resolved the assigment path,
                # don't infer the last part
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
    if asspath is None:
        for lst in self.iter.infer(context):
            if isinstance(lst, (Tuple, List)):
                for item in lst.elts:
                    yield item
    else:
        for infered in _resolve_looppart(self.iter.infer(context), asspath, context):
            yield infered
nodes.For.assigned_stmts = raise_if_nothing_infered(for_assigned_stmts)
nodes.Comprehension.assigned_stmts = raise_if_nothing_infered(for_assigned_stmts)


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


def _arguments_infer_argname(self, name, context):
    # arguments informmtion may be missing, in which case we can't do anything
    # more
    if not (self.args or self.vararg or self.kwarg):
        yield YES
        return
    # first argument of instance/class method
    if self.args and getattr(self.args[0], 'name', None) == name:
        functype = self.parent.type
        if functype == 'method':
            yield Instance(self.parent.parent.frame())
            return
        if functype == 'classmethod':
            yield self.parent.parent.frame()
            return
    if name == self.vararg:
        yield const_factory(())
        return
    if name == self.kwarg:
        yield const_factory({})
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
        

def assign_assigned_stmts(self, node, context=None, asspath=None):
    if not asspath:
        yield self.value
        return
    for infered in _resolve_asspart(self.value.infer(context), asspath, context):
        yield infered
nodes.Assign.assigned_stmts = raise_if_nothing_infered(assign_assigned_stmts)
nodes.AugAssign.assigned_stmts = raise_if_nothing_infered(assign_assigned_stmts)


def _resolve_asspart(parts, asspath, context):
    """recursive function to resolve multiple assignments"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if hasattr(part, 'getitem'):
            try:
                assigned = part.getitem(index, context)
            # XXX raise a specific exception to avoid potential hiding of
            # unexpected exception ?
            except (TypeError, IndexError):
                return
            if not asspath:
                # we acheived to resolved the assigment path, don't infer the
                # last part
                yield assigned
            elif assigned is YES:
                return
            else:
                # we are not yet on the last part of the path search on each
                # possibly infered value
                try:
                    for infered in _resolve_asspart(assigned.infer(context), 
                                                    asspath, context):
                        yield infered
                except InferenceError:
                    return

    
def excepthandler_assigned_stmts(self, node, context=None, asspath=None):
    for assigned in unpack_infer(self.type):
        if isinstance(assigned, Class):
            assigned = Instance(assigned)
        yield assigned
nodes.ExceptHandler.assigned_stmts = raise_if_nothing_infered(excepthandler_assigned_stmts)


def with_assigned_stmts(self, node, context=None, asspath=None):
    if asspath is None:
        for lst in self.vars.infer(context):
            if isinstance(lst, (Tuple, List)):
                for item in lst.nodes:
                    yield item
nodes.With.assigned_stmts = raise_if_nothing_infered(with_assigned_stmts)


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

# XXX if you add ass_type to a class, you should probably modify
#     lookup.filter_stmts around line ::
#
#       if ass_type is mystmt and not isinstance(ass_type, (nodes.Class, ...)):
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


# callable protocol ###########################################################

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
    returns = self.nodes_of_class(nodes.Return, skip_klass=Function)
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


# iteration protocol ##########################################################
        
def const_itered(self):
    if isinstance(self.value, basestring):
        return self.value
    raise TypeError()
nodes.Const.itered = const_itered

        
def tl_itered(self):
    return self.elts
nodes.Tuple.itered = tl_itered
nodes.List.itered = tl_itered

        
def dict_itered(self):
    return self.items[::2]
nodes.Dict.itered = dict_itered


# subscription protocol #######################################################
                
def const_getitem(self, index, context=None):
    if isinstance(self.value, basestring):
        return self.value[index]
    raise TypeError()
nodes.Const.getitem = const_getitem


def tl_getitem(self, index, context=None):
    return self.elts[index]
nodes.Tuple.getitem = tl_getitem
nodes.List.getitem = tl_getitem


def dict_getitem(self, key, context=None):
    for i in xrange(0, len(self.items), 2):
        for inferedkey in self.items[i].infer(context):
            if inferedkey is YES:
                continue
            if isinstance(inferedkey, Const) and inferedkey.value == key:
                return self.items[i+1]
    raise IndexError(key)
nodes.Dict.getitem = dict_getitem

