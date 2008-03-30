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
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2008 Sylvain Thenault
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
    for special_key in ('__doc__', '__module__', '__dict__'):
        if special_key in addons.__dict__:
            del brain[special_key]
    try:
        original.__dict__.update(brain)
    except AttributeError:
        # dictproxy object
        for k, v in brain.iteritems():
            setattr(original, k, v)
        
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
        
    def walk(self, node, _done=None):
        """walk on the tree from <node>, getting callbacks from handler
        """
        if _done is None:
            _done = set()
        if node in _done:
            raise AssertionError((id(node), node.parent))
        _done.add(node)
        try:            
            self.visit(node)
        except IgnoreChild:
            pass
        else:
            print 'visit', node, id(node)
            try:
                for child_node in node.getChildNodes():
                    assert child_node is not node
                    self.walk(child_node, _done)
            except AttributeError:
                print node.__class__, id(node.__class__)
                raise
        self.leave(node)
        assert node.parent is not node

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


# special inference objects ###################################################

class Yes(object):
    """a yes object"""
    def __repr__(self):
        return 'YES'
    def __getattribute__(self, name):
        return self
    def __call__(self, *args, **kwargs):
        return self

YES = Yes()

class Proxy:
    """a simple proxy object"""
    def __init__(self, proxied):
        self._proxied = proxied

    def __getattr__(self, name):
        return getattr(self._proxied, name)

    def infer(self, context=None):
        yield self


class InstanceMethod(Proxy):
    """a special node representing a function bound to an instance"""
    def __repr__(self):
        instance = self._proxied.parent.frame()
        return 'Bound method %s of %s.%s' % (self._proxied.name,
                                             instance.root().name,
                                             instance.name)
    __str__ = __repr__

    def is_bound(self):
        return True


class Instance(Proxy):
    """a special node representing a class instance"""
    def getattr(self, name, context=None, lookupclass=True):
        try:
            return self._proxied.instance_attr(name, context)
        except NotFoundError:
            if name == '__class__':
                return [self._proxied]
            if name == '__name__':
                # access to __name__ gives undefined member on class
                # instances but not on class objects
                raise NotFoundError(name)
            if lookupclass:
                return self._proxied.getattr(name, context)
        raise NotFoundError(name)

    def igetattr(self, name, context=None):
        """infered getattr"""
        try:
            # XXX frame should be self._proxied, or not ?
            return _infer_stmts(
                self._wrap_attr(self.getattr(name, context, lookupclass=False)),
                                context, frame=self)
        except NotFoundError:
            try:
                # fallback to class'igetattr since it has some logic to handle
                # descriptors
                return self._wrap_attr(self._proxied.igetattr(name, context))
            except NotFoundError:
                raise InferenceError(name)
            
    def _wrap_attr(self, attrs):
        """wrap bound methods of attrs in a InstanceMethod proxies"""
        # Guess which attrs are used in inference.
        def wrap(attr):
            if isinstance(attr, Function) and attr.type == 'method':
                return InstanceMethod(attr)
            else:
                return attr
        return imap(wrap, attrs)
        
    def infer_call_result(self, caller, context=None):
        """infer what's a class instance is returning when called"""
        infered = False
        for node in self._proxied.igetattr('__call__', context):
            for res in node.infer_call_result(caller, context):
                infered = True
                yield res
        if not infered:
            raise InferenceError()

    def __repr__(self):
        return 'Instance of %s.%s' % (self._proxied.root().name,
                                      self._proxied.name)
    __str__ = __repr__
    
    def callable(self):
        try:
            self._proxied.getattr('__call__')
            return True
        except NotFoundError:
            return False

    def pytype(self):
        return self._proxied.qname()
    
class Generator(Proxy): 
    """a special node representing a generator"""
    def callable(self):
        return True
    
    def pytype(self):
        return '__builtin__.generator'

# additional nodes  ##########################################################

class NoneType(Instance):
    """None value (instead of Name('None')"""
    
NONE = NoneType(None)

class Bool(Instance):
    """None value (instead of Name('True') / Name('False')"""
    def __init__(self, value):
        self.value = value
TRUE = Bool(True)
FALSE = Bool(True)

# inference utilities #########################################################

def infer_end(self, context=None):
    """inference's end for node such as Module, Class, Function, Const...
    """
    yield self

def end_ass_type(self):
    return self
