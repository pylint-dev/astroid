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
"""Monkey patch compiler.transformer to fix line numbering bugs

:author:    Sylvain Thenault
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2008 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

from types import TupleType
from compiler import transformer

from logilab.astng import nodes

def fromto_lineno(asttuple):
    """return the minimum and maximum line number of the given ast tuple"""
    return from_lineno(asttuple), to_lineno(asttuple)

def from_lineno(asttuple):
    """return the minimum line number of the given ast tuple"""
    if type(asttuple[1]) is TupleType:
        return from_lineno(asttuple[1])
    return asttuple[2]

def to_lineno(asttuple):
    """return the maximum line number of the given ast tuple"""
    if type(asttuple[-1]) is TupleType:
        return to_lineno(asttuple[-1])
    return asttuple[2]

def fix_lineno(node, fromast, toast=None):
    if 'fromlineno' in node.__dict__:
        return node    
    #print 'fixing', id(node), id(node.__dict__), node.__dict__.keys(), repr(node)
    if isinstance(node, nodes.Stmt):
        node.fromlineno = from_lineno(fromast)#node.nodes[0].fromlineno
        node.tolineno = node.nodes[-1].tolineno
        return node
    if toast is None:
        node.fromlineno, node.tolineno = fromto_lineno(fromast)
    else:
        node.fromlineno, node.tolineno = from_lineno(fromast), to_lineno(toast)
    #print 'fixed', id(node)
    return node

BaseTransformer = transformer.Transformer

COORD_MAP = {
    # if: test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
    'if': (0, 0),
    # 'while' test ':' suite ['else' ':' suite]
    'while': (0, 1),
    # 'for' exprlist 'in' exprlist ':' suite ['else' ':' suite]
    'for': (0, 3),
    # 'try' ':' suite (except_clause ':' suite)+ ['else' ':' suite]
    'try': (0, 0),
    # | 'try' ':' suite 'finally' ':' suite
    
    }

def fixlineno_wrap(function, stype):
    def fixlineno_wrapper(self, nodelist):
        node = function(self, nodelist)            
        idx1, idx2 = COORD_MAP.get(stype, (0, -1))
        return fix_lineno(node, nodelist[idx1], nodelist[idx2])
    return fixlineno_wrapper

class ASTNGTransformer(BaseTransformer):
    """ovverides transformer for a better source line number handling"""
    def com_NEWLINE(self, *args):
        # A ';' at the end of a line can make a NEWLINE token appear
        # here, Render it harmless. (genc discards ('discard',
        # ('const', xxxx)) Nodes)
        lineno = args[0][1]
        # don't put fromlineno/tolineno on Const None to mark it as dynamically
        # added, without "physical" reference in the source
        n = nodes.Discard(nodes.Const(None))
        n.fromlineno = n.tolineno = lineno
        return n    
    def com_node(self, node):
        res = self._dispatch[node[0]](node[1:])
        return fix_lineno(res, node)
    def com_assign(self, node, assigning):
        res = BaseTransformer.com_assign(self, node, assigning)
        return fix_lineno(res, node)
    def com_apply_trailer(self, primaryNode, nodelist):
        node = BaseTransformer.com_apply_trailer(self, primaryNode, nodelist)
        return fix_lineno(node, nodelist)
    
##     def atom(self, nodelist):
##         node = BaseTransformer.atom(self, nodelist)
##         return fix_lineno(node, nodelist[0], nodelist[-1])
    
    def funcdef(self, nodelist):
        node = BaseTransformer.funcdef(self, nodelist)
        # XXX decorators
        return fix_lineno(node, nodelist[-5], nodelist[-3])
    def classdef(self, nodelist):
        node = BaseTransformer.classdef(self, nodelist)
        return fix_lineno(node, nodelist[0], nodelist[-2])
            
# wrap *_stmt methods
for name in dir(BaseTransformer):
    if name.endswith('_stmt') and not (name in ('com_stmt',
                                                'com_append_stmt')
                                       or name in ASTNGTransformer.__dict__):
        setattr(BaseTransformer, name,
                fixlineno_wrap(getattr(BaseTransformer, name), name[:-5]))
            
transformer.Transformer = ASTNGTransformer

