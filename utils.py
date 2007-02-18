# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""this module contains some utilities to navigate in the tree or to
extract information from it

:author:    Sylvain Thenault
:copyright: 2003-2007 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2007 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__docformat__ = "restructuredtext en"

from logilab.common.compat import enumerate
from logilab.astng._exceptions import IgnoreChild

def extend_class(original, addons):
    """add methods and attribute defined in the addons class to the original
    class
    """
    brain = addons.__dict__.copy()
    for special_key in ('__doc__', '__module__'):
        if special_key in addons.__dict__:
            del brain[special_key]
    original.__dict__.update(brain)
        
class ASTWalker:
    """a walker visiting a tree in preorder, calling on the handler:
    
    * visit_<class name> on entering a node, where class name is the class of
    the node in lower case
    
    * leave_<class name> on leaving a node, where class name is the class of
    the node in lower case
    """
    def __init__(self, handler):
        self.handler = handler
        self._cache = {}
        
    def walk(self, node):
        """walk on the tree from <node>, getting callbacks from handler
        """
        try:            
            self.visit(node)
        except IgnoreChild:
            pass
        else:
            for child_node in node.getChildNodes():
                self.walk(child_node)
        self.leave(node)

    def get_callbacks(self, node):
        """get callbacks from handler for the visited node
        """
        klass = node.__class__
        methods = self._cache.get(klass)
        if methods is None:
            handler = self.handler
            kid = klass.__name__.lower()
            e_method = getattr(handler, 'visit_%s' % kid,
                               getattr(handler, 'visit_default', None))
            l_method = getattr(handler, 'leave_%s' % kid, 
                               getattr(handler, 'leave_default', None))
            self._cache[klass] = (e_method, l_method)
        else:
            e_method, l_method = methods
        return e_method, l_method
    
    def visit(self, node):
        """walk on the tree from <node>, getting callbacks from handler"""
        method = self.get_callbacks(node)[0]
        if method is not None:
            method(node)
            
    def leave(self, node):
        """walk on the tree from <node>, getting callbacks from handler"""
        method = self.get_callbacks(node)[1]
        if method is not None:
            method(node)


class LocalsVisitor(ASTWalker):
    """visit a project by traversing the locals dictionnary"""
    def __init__(self):
        ASTWalker.__init__(self, self)
        self._visited = {}
        
    def visit(self, node):
        """launch the visit starting from the given node"""
        if self._visited.has_key(node):
            return
        self._visited[node] = 1
        methods = self.get_callbacks(node)
        recurse = 1
        if methods[0] is not None:
            try:
                methods[0](node)
            except IgnoreChild:
                recurse = 0
        if recurse:
            if hasattr(node, 'locals'):
                for local_node in node.values():
                    self.visit(local_node)
        if methods[1] is not None:
            return methods[1](node)

def are_exclusive(stmt1, stmt2):
    """return true if the two given statement are mutually exclusive

    algorithm :
     1) index stmt1's parents
     2) climb among stmt2's parents until we find a common parent
     3) if the common parent is a If or TryExcept statement, look if nodes are
        in exclusive branchs
    """
    from logilab.astng.nodes import If, TryExcept
    # index stmt1's parents
    stmt1_parents = {}
    children = {}
    node = stmt1.parent
    previous = stmt1
    while node:
        stmt1_parents[node] = 1
        children[node] = previous
        previous = node
        node = node.parent
    # climb among stmt2's parents until we find a common parent
    node = stmt2.parent
    previous = stmt2
    while node:
        if stmt1_parents.has_key(node):
            # if the common parent is a If or TryExcept statement, look if
            # nodes are in exclusive branchs
            if isinstance(node, If):
                if previous != children[node]:
                    return True
            elif isinstance(node, TryExcept):
                stmt1_previous = children[node]
                if not previous is stmt1_previous:
                    stmt1_branch, stmt1_num = _try_except_from_branch(node, stmt1_previous)
                    stmt2_branch, stmt2_num = _try_except_from_branch(node, previous)
                    if stmt1_branch != stmt1_branch:
                        if not ((stmt2_branch == 'body' and stmt1_branch == 'else') or
                                (stmt1_branch == 'body' and stmt2_branch == 'else') or
                                (stmt2_branch == 'body' and stmt1_branch == 'except') or
                                (stmt1_branch == 'body' and stmt2_branch == 'except')):
                            return True
                    elif stmt1_num != stmt2_num:
                        return True
            return False
        previous = node
        node = node.parent
    return False

def _try_except_from_branch(node, stmt):
    if stmt is node.body:
        return 'body', 1
    if stmt is node.else_:
        return 'else', 1
    for i, block_nodes in enumerate(node.handlers):
        if stmt in block_nodes:
            return 'except', i
