'''This contains an implementation of a zipper for astroid ASTs.

A zipper is a data structure for traversing and editing immutable
recursive data types that can act as a doubly-linked structure without
actual double links.
http://blog.ezyang.com/2010/04/you-could-have-invented-zippers/ has a
brief introduction to zippers as a whole.  This implementation is
based on the Clojure implementation,
https://github.com/clojure/clojure/blob/master/src/clj/clojure/zip.clj .

'''
import collections

# Because every zipper method creates a new zipper, zipper creation
# has to be optimized as much as possible.  Using wrapt here instead
# of lazy_object_proxy avoids several additional function calls every
# time an AST node method has to be accessed through a new zipper.
import wrapt

from astroid import context
from astroid import exceptions
from astroid import inference
from astroid.interpreter import scope
from astroid.tree import base
from astroid.tree import treeabc


# The following are helper functions for working with singly-linked
# lists made with two-tuples.  The empty tuple is used to denote the
# end of a linked list.  The zipper needs singly-linked lists for most
# of its operations to take constant time.
def linked_list(*values):
    '''Builds a new linked list of tuples out of its arguments.'''
    tail = ()
    for value in reversed(values):
        tail = (value, tail)
    return tail

def reverse(linked_list):
    '''Reverses an existing linked list of tuples.'''
    if linked_list:
        result = collections.deque((linked_list[0],))
        tail = linked_list[1]
        while tail:
            result.appendleft(tail[0])
            tail = tail[1]
        tail = (result.pop(), ())
        while result:
            tail = (result.pop(), tail)
        return tail

def iterate(linked_list):
    '''Return an iterator over a linked list of tuples.'''
    node = linked_list
    while node:
        yield node[0]
        node = node[1]

def concatenate(left, right):
    '''Takes two existing linked lists of tuples and concatenates the
    first one onto the second.

    '''
    if not left:
        return right
    elif not right:
        return left
    else:
        result = [left[0]]
        tail = left[1]
        while tail:
            result.append(tail[0])
            tail = tail[1]
        tail = (result.pop(), right)
        while result:
            tail = (result.pop(), tail)
        return tail

def last(linked_list):
    '''Returns the last element of a linked list of tuples.'''
    node = linked_list
    while node[1]:
        node = node[1]
    return node[0]

def initial(linked_list):
    '''Returns a linked list of tuples containing all elements but the last.'''
    result = [linked_list[0]]
    tail = linked_list[1]
    while tail:
        result.append(tail[0])
        tail = tail[1]
    result.pop()
    while result:
        tail = (result.pop(), tail)
    return tail


# Attributes:
#     left (linked list): The siblings to the left of the zipper's focus.
#     right (linked list): The siblings to the right of the zipper's focus.
#     parent_nodes (linked list): The ancestors of the zipper's focus
#     parent_path (Path): The Path from the zipper that created this zipper.
#     changed (bool): Whether this zipper has been edited or not.
Path = collections.namedtuple('Path', 'left right parent_nodes parent_path changed')

class Zipper(wrapt.ObjectProxy):
    '''This an object-oriented version of a zipper with methods instead of
    functions.  All the methods return a new zipper or None, and none
    of them mutate the underlying AST nodes.  They return None when
    the method is not valid for that zipper.  The zipper acts as a
    proxy so the underlying node's or sequence's methods and
    attributes are accessible through it.

    Attributes:
        __wrapped__ (base.NodeNG, collections.Sequence): The AST node or
            sequence at the zipper's focus.
        _self_path (Path): The Path tuple containing information about the
            zipper's history.  This must be accessed as ._self_path.

    '''
    __slots__ = ('path')

    # Setting wrapt.ObjectProxy.__init__ as a default value turns it
    # into a local variable, avoiding a super() call, two globals
    # lookups, and two dict lookups (on wrapt's and ObjectProxy's
    # dicts) in the most common zipper operation on CPython.
    def __init__(self, focus, path=None, _init=wrapt.ObjectProxy.__init__):
        '''Make a new zipper.

        Arguments:
            focus (base.NodeNG, collections.Sequence): The focus for this
                zipper, will be assigned to self.__wrapped__ by
                wrapt.ObjectProxy's __init__.
            path: The path of the zipper used to create the new zipper, if any.

        Returns:
            A new zipper object.
        '''
        _init(self, focus)
        self._self_path = path


    # Traversal
    def left(self):
        '''Go to the next sibling that's directly to the left of the focus.

        This takes constant time.'''
        if self._self_path and self._self_path.left:
            focus, left = self._self_path.left
            path = self._self_path._replace(left=left,
                                            right=(self.__wrapped__,
                                                   self._self_path.right))
            return type(self)(focus=focus, path=path)

    def leftmost(self):
        '''Go to the leftmost sibling of the focus.

        This takes time linear in the number of left siblings.'''
        if self._self_path and self._self_path.left:
            focus, siblings = last(self._self_path.left), initial(self._self_path.left) 
            path = self._self_path._replace(left=(), right=concatenate(reverse(siblings), (self.__wrapped__, self._self_path.right)))
            return type(self)(focus=focus, path=path)

    def right(self):
        '''Go to the next sibling that's directly to the right of the focus.

        This takes constant time.'''
        if self._self_path and self._self_path.right:
            focus, right = self._self_path.right
            path = self._self_path._replace(left=(self.__wrapped__,
                                                  self._self_path.left),
                                            right=right)
            return type(self)(focus=focus, path=path)

    def rightmost(self):
        '''Go to the rightmost sibling of the focus.

        This takes time linear in the number of right siblings.'''
        if self._self_path and self._self_path.right:
            siblings, focus = initial(self._self_path.right), last(self._self_path.right)
            path = self._self_path._replace(left=concatenate(reverse(siblings), (self.__wrapped__, self._self_path.left)),
                                            right=())
            return type(self)(focus=focus, path=path)

    def down(self):
        '''Go to the leftmost child of the focus.

        This takes constant time.'''
        try:
            children = iter(self.__wrapped__)
            first = next(children)
        except StopIteration:
            return
        path = Path(
            left=(),
            right=linked_list(*children),
            parent_nodes=(self.__wrapped__, self._self_path.parent_nodes) if self._self_path else (self.__wrapped__, ()),
            parent_path=self._self_path,
            changed=False)
        return type(self)(focus=first, path=path)

    def up(self):
        '''Go to the parent of the focus.

        This takes time linear in the number of left siblings if the
        focus has been edited or constant time if it hasn't been
        edited.

        '''
        if self._self_path:
            left, right, parent_nodes, parent_path, changed = self._self_path
            if parent_nodes:
                focus = parent_nodes[0]
                # This conditional uses parent_nodes to make going up
                # take constant time if the focus hasn't been edited.
                if changed:
                    return type(self)(
                        focus=focus.make_node(concatenate(reverse(left), (self.__wrapped__, right))),
                        path=parent_path and parent_path._replace(changed=True))
                else:
                    return type(self)(focus=focus, path=parent_path)

    def root(self):
        '''Go to the root of the AST for the focus.

        This takes time linear in the number of ancestors of the focus.'''
        location = self
        while location._self_path:
            location = location.up()
        return location

    def common_ancestor(self, other):
        '''Find the most recent common ancestor of two different zippers.

        This takes time linear in the number of ancestors of both foci
        and will return None for zippers from two different ASTs.  The
        new zipper is derived from the zipper the method is called on,
        so edits in the second argument will not be included in the
        new zipper.

        '''
        if self._self_path:
            self_ancestors = reverse((self.__wrapped__, self._self_path.parent_nodes))
        else:
            self_ancestors = (self.__wrapped__, ())
        if other._self_path:
            other_ancestors = reverse((other.__wrapped__, other._self_path.parent_nodes))
        else:
            other_ancestors = (other.__wrapped__, ())
        ancestor = None
        for self_ancestor, other_ancestor in zip(iterate(self_ancestors), iterate(other_ancestors)):
            # This is a kludge to work around the problem of two Empty
            # nodes in different parts of an AST.  Empty nodes can
            # never be ancestors, so they can be safely skipped.
            if self_ancestor is other_ancestor and not isinstance(self_ancestor, treeabc.Empty):
                ancestor = self_ancestor
            else:
                break
        if ancestor is None:
            return None
        else:
            location = self
            while location.__wrapped__ is not ancestor:
                location = location.up()
        return location

    def children(self):
        '''Iterates over the children of the focus.'''
        child = self.down()
        while child is not None:
            yield child
            child = child.right()

    # Iterative algorithms for these two methods, with explicit
    # stacks, avoid the problem of yield from only being available on
    # Python 3 and ensure that no AST will overflow the call stack.
    # On CPython, avoiding the extra function calls necessary for a
    # recursive algorithm will probably make them faster too.
    def preorder_descendants(self, dont_recurse_on=None):
        '''Iterates over the descendants of the focus in prefix order.

        Arguments:
            dont_recurse_on (base.NodeNG): If not None, will not include nodes
                of this type or types or any of the descendants of those nodes.
        '''
        to_visit = [self]
        while to_visit:
            location = to_visit.pop()
            yield location
            if dont_recurse_on is None:
                to_visit.extend(c for c in
                                reversed(tuple(location.children())))
            else:
                to_visit.extend(c for c in
                                reversed(tuple(location.children()))
                                if not isinstance(c, dont_recurse_on))

    def postorder_descendants(self, dont_recurse_on=None):
        '''Iterates over the descendants of the focus in postfix order.

        Arguments:
            dont_recurse_on (base.NodeNG): If not None, will not include nodes
                of this type or types or any of the descendants of those nodes.
        '''
        to_visit = [self]
        visited_ancestors = []
        while to_visit:
            location = to_visit[-1]
            if not visited_ancestors or visited_ancestors[-1] is not location:
                visited_ancestors.append(location)
                if dont_recurse_on is None:
                    to_visit.extend(c for c in
                                    reversed(tuple(location.children())))
                else:
                    to_visit.extend(c for c in
                                    reversed(tuple(location.children()))
                                    if not isinstance(c, dont_recurse_on))
                continue
            visited_ancestors.pop()
            yield location
            to_visit.pop()

    def find_descendants_of_type(self, cls, skip_class=None):
        '''Iterates over the descendants of the focus of a given type in
        prefix order.

        Arguments:
            skip_class (base.NodeNG, tuple(base.NodeNG)): If not None, will
                not include nodes of this type or types or any of the
                descendants of those nodes.
        '''
        return (d for d in self.preorder_descendants(skip_class) if isinstance(d, cls))
        # if isinstance(self, cls):
        #     yield self
        # child = self.down()
        # while child:
        #     if skip_class is not None and isinstance(location, skip_class):
        #         continue
        #     for matching in child.nodes_of_class(cls, skip_class):
        #         yield matching
        #     child = child.right()
        #     if isinstance(child, collections.Sequence):
        #         child = child.down()

    # Editing
    def replace(self, focus):
        '''Replaces the existing node at the focus.

        Arguments:
            focus (base.NodeNG, collections.Sequence): The object to replace
                the focus with.
        '''
        return type(self)(focus=focus, path=self._self_path._replace(changed=True))
    
    # def edit(self, *args, **kws):
    #     return type(self)(focus=self.__wrapped__.make_focus(*args, **kws),
    #                       path=self._self_path._replace(changed=True))

    
    # Legacy APIs
    @property
    def parent(self):
        '''Goes up to the next ancestor of the focus that's a node, not a
        sequence.'''
        location = self.up()
        if isinstance(location, collections.Sequence):
            return location.up()
        else:
            return location

    def get_children(self):
        '''Iterates over nodes that are children or grandchildren, no
        sequences.

        '''
        child = self.down()
        while child is not None:
            if isinstance(child, collections.Sequence):
                grandchild = child.down()
                for _ in range(len(child)):
                    yield grandchild
                    grandchild = grandchild.right()
            else:
                yield child
            child = child.right()

    def last_child(self):
        return self.rightmost()

    def next_sibling(self):
        return self.right()

    def previous_sibling(self):
        return self.left()

    def nodes_of_class(self, cls, skip_class=None):
        return self.find_descendants_of_type(cls, skip_class)

    # def child_sequence(self, child):
    #     return self.locate_child(child)[1]

    # def child_sequence(self, child):
    #     """search for the right sequence where the child lies in"""
    #     location = self.down()
    #     while location:
    #         if location is child:
    #             return location
    #         if (isinstance(location, collections.Sequence)
    #             and child in location):
    #             return location
    #     msg = 'Could not find %s in %s\'s children'
    #     raise exceptions.AstroidError(msg % (repr(child), repr(self)))

    # def locate_child(self, child):
    #     """return a 2-uple (child attribute name, sequence or node)"""
    #     location = self.down()
    #     index = 0
    #     while location:
    #         if location is child:
    #             return self._astroid_fields[index], location
    #         if (isinstance(location, collections.Sequence)
    #             and child in location):
    #             return self._astroid_fields[index], location
    #         index += 1
    #     msg = 'Could not find %s in %s\'s children'
    #     raise exceptions.AstroidError(msg % (repr(child), repr(self)))
    # # FIXME : should we merge child_sequence and locate_child ? locate_child
    # # is only used in are_exclusive, child_sequence one time in pylint.

    def frame(self):
        '''Go to the first ancestor of the focus that creates a new frame.

        This takes time linear in the number of ancestors of the focus.'''
        location = self
        while (location is not None and 
               not isinstance(location.__wrapped__,
                              (treeabc.FunctionDef, treeabc.Lambda,
                               treeabc.ClassDef, treeabc.Module))):
            location = location.up()
        return location

    def infer(self, context=None, **kwargs):
        """main interface to the interface system, return a generator on inferred
        values.

        If the instance has some explicit inference function set, it will be
        called instead of the default interface.
        """
        if self._explicit_inference is not None:
            # explicit_inference is not bound, give it self explicitly
            try:
                # pylint: disable=not-callable
                return self._explicit_inference(self, context, **kwargs)
            except exceptions.UseInferenceDefault:
                pass

        if not context:
            return inference.infer(self, context, **kwargs)

        key = (self, context.lookupname,
               context.callcontext, context.boundnode)
        if key in context.inferred:
            return iter(context.inferred[key])

        return context.cache_generator(key, inference.infer(self, context, **kwargs))

    def scope(self):
        """Get the first node defining a new scope

        Scopes are introduced in Python 3 by Module, FunctionDef,
        ClassDef, Lambda, GeneratorExp, and comprehension nodes.  On
        Python 2, the same is true except that list comprehensions
        don't generate a new scope.

        """
        return scope.node_scope(self)

    def statement(self):
        '''Go to the first ancestor of the focus that's a Statement.

        This takes time linear in the number of ancestors of the focus.'''
        location = self
        while (location is not None and 
               not isinstance(location.__wrapped__,
                              (treeabc.Module, treeabc.Statement))):
            location = location.up()
        return location
