# Copyright (c) 2003 Sylvain Thenault (thenault@nerim.net)
# Copyright (c) 2003 Logilab
#
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
"""Some usefull functions to manipulate ast tuples
"""

__author__ = u"Sylvain Thenault"

import symbol
import token
from types import TupleType

def debuild(ast_tuple):
    """
    reverse ast_tuple to string
    """
    if type(ast_tuple[1]) is TupleType:
        result = ''
        for child in ast_tuple[1:]: 
            result = '%s%s' % (result, debuild(child))
        return result
    else:
        return ast_tuple[1]

def clean(ast_tuple):
    """
    reverse ast tuple to a list of tokens
    merge sequences (token.NAME, token.DOT, token.NAME)
    """
    result = []
    last = None
    for couple in _clean(ast_tuple):
        if couple[0] == token.NAME and last == token.DOT:
            result[-1][1] += couple[1]
        elif couple[0] == token.DOT and last == token.NAME:
            result[-1][1] += couple[1]
        else:
            result.append(couple)
        last = couple[0]
    return result

def _clean(ast_tuple):
    """ transform the ast into as list of tokens (i.e. final elements)
    """
    if type(ast_tuple[1]) is TupleType:
        v = []
        for c in ast_tuple[1:]:
            v += _clean(c)
        return v
    else:
        return [list(ast_tuple[:2])]
    
def cvrtr(tuple):
    """debug method returning an ast string in a readable fashion"""
    if type(tuple) is TupleType:
        try:
            try:
                txt = 'token.'+token.tok_name[tuple[0]]
            except:
                txt = 'symbol.'+symbol.sym_name[tuple[0]]
        except:
            txt =  'Unknown token/symbol'
        return [txt] + map(cvrtr, tuple[1:])
    else:
        return tuple

__all__ = ('debuild', 'clean', 'cvrtr')
