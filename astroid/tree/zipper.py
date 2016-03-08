import collections

# Because every zipper method creates a new zipper, zipper creation
# has to be optimized as much as possible.  Using wrapt here instead
# of lazy_object_proxy avoids several additional function calls every
# time an AST node method has to be accessed through a new zipper.
import wrapt

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


Path = collections.namedtuple('Path', 'left right parent_nodes parent_path changed')

class Zipper(wrapt.ObjectProxy):
    __slots__ = ('path')

    # Setting wrapt.ObjectProxy.__init__ as a default value turns it into a
    # local variable, avoiding a super() call, two globals lookups,
    # and two dict lookups (on wrapt's and ObjectProxy's dicts).
    def __init__(self, focus, path=None, init=wrapt.ObjectProxy.__init__):
        init(self, focus)
        self._self_path = path

    # Traversal
    def left(self):
        if self._self_path and self._self_path.left:
            focus, left = self._self_path.left
            path = self._self_path._replace(left=left,
                                            right=(self.__wrapped__,
                                                   self._self_path.right))
            return type(self)(focus=focus, path=path)

    def leftmost(self):
        if self._self_path and self._self_path.left:
            focus, siblings = last(self._self_path.left), initial(self._self_path.left) 
            path = self._self_path._replace(left=(), right=concatenate(reverse(siblings), (self.__wrapped__, self._self_path.right)))
            return type(self)(focus=focus, path=path)

    def right(self):
        if self._self_path and self._self_path.right:
            focus, right = self._self_path.right
            path = self._self_path._replace(left=(self.__wrapped__,
                                                  self._self_path.left),
                                            right=right)
            return type(self)(focus=focus, path=path)

    def rightmost(self):
        if self._self_path and self._self_path.right:
            siblings, focus = initial(self._self_path.right), last(self._self_path.right)
            path = self._self_path._replace(left=concatenate(reverse(siblings), (self.__wrapped__, self._self_path.left)),
                                            right=())
            return type(self)(focus=focus, path=path)

    def down(self):
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
        if self._self_path:
            left, right, parent_nodes, parent_path, changed = self._self_path
            if parent_nodes:
                focus = parent_nodes[0]
                if changed:
                    return type(self)(
                        focus=focus.make_node(concatenate(reverse(left), (self.__wrapped__, right))),
                        path=parent_path and parent_path._replace(changed=True))
                else:
                    return type(self)(focus=focus, path=parent_path)

    def root(self):
        """return the root node of the tree"""
        location = self
        while location._self_path:
            location = location.up()
        return location

    def common_ancestor(self, other):
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

    def get_children(self):
        child = self.down()
        while child is not None:
            yield child
            child = child.right()

    def preorder_descendants(self, dont_recurse_on=None):
        to_visit = [self]
        while to_visit:
            location = to_visit.pop()
            yield location
            if dont_recurse_on is None:
                to_visit.extend(c for c in
                                reversed(tuple(location.get_children())))
            else:
                to_visit.extend(c for c in
                                reversed(tuple(location.get_children()))
                                if not isinstance(c, dont_recurse_on))

    def postorder_descendants(self, dont_recurse_on=None):
        to_visit = [self]
        visited_ancestors = []
        while to_visit:
            location = to_visit[-1]
            if not visited_ancestors or visited_ancestors[-1] is not location:
                visited_ancestors.append(location)
                if dont_recurse_on is None:
                    to_visit.extend(c for c in
                                    reversed(tuple(location.get_children())))
                else:
                    to_visit.extend(c for c in
                                    reversed(tuple(location.get_children()))
                                    if not isinstance(c, dont_recurse_on))
                continue
            visited_ancestors.pop()
            yield location
            to_visit.pop()

    def find_descendants_of_type(self, cls, skip_class=None):
        """return an iterator on nodes which are instance of the given class(es)

        cls may be a class object or a tuple of class objects
        """
        return (d for d in self.preorder_descendants(skip_class) if isinstance(node, cls))
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


    # Legacy APIs
    @property
    def parent(self):
        location = self.up()
        if isinstance(location, collections.Sequence):
            return location.up()
        else:
            return location

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

    # Editing
    def replace(self, focus):
        return type(self)(focus=focus, path=self._self_path._replace(changed=True))

    # def edit(self, *args, **kws):
    #     return type(self)(focus=self.__wrapped__.make_focus(*args, **kws),
    #                       path=self._self_path._replace(changed=True))
