import collections

# Because every zipper method creates a new zipper, zipper creation
# has to be optimized as much as possible.  Using wrapt here instead
# of lazy_object_proxy avoids several additional function calls every
# time an AST node method has to be accessed through a new zipper.
# Importing ObjectProxy into the local name space avoids an extra
# indirection during initialization.
from wrapt import ObjectProxy as _ObjectProxy


# The following are helper functions for working with singly-linked
# lists made with two-tuples.  The zipper needs singly-linked lists
# for most of its operations to take constant time.
def linked_list(*values, **kws):
    '''Builds a new linked list of tuples out of its arguments, appending
    to the front of an existing list if that's given.

    :param values: The values to add to the front of list.

    :param tail: The existing list to append to.  Must be provided as 
        a keyword argument and not required.

    '''
    if values:
        # The use of varkws here is a workaround for the lack of
        # keyword-only arguments on Python 2.
        tail = (values[-1], kws.get('tail', None))
        for value in reversed(values[:-1]):
            tail = (value, tail)
        return tail
    else:
        return None

def reverse(linked_list):
    '''Reverses an existing linked list of tuples.'''
    if linked_list:
        result = collections.deque((linked_list[0],))
        tail = linked_list[1]
        while tail is not None:
            result.appendleft(tail[0])
            tail = tail[1]
        tail = (result.pop(), None)
        while result:
            tail = (result.pop(), tail)
        return tail

def iterate(linked_list):
    '''Return an iterator over a linked list of tuples.'''
    node = linked_list
    while node is not None:
        yield node[0]
        node = node[1]

def concatenate(left, right):
    '''Takes two existing linked lists of tuples and concatenates the
    first one onto the second.

    '''
    if left is None:
        return right
    elif right is None:
        return left
    else:
        result = [left[0]]
        tail = left[1]
        while tail is not None:
            result.append(tail[0])
            tail = tail[1]
        tail = (result.pop(), right)
        while result:
            tail = (result.pop(), tail)
        return tail

def last(linked_list):
    node = linked_list
    while node[1] is not None:
        node = node[1]
    return node

def initial(linked_list):
    result = [linked_list[0]]
    tail = linked_list[1]
    while tail is not None:
        result.append(tail[0])
        tail = tail[1]
    result.pop()
    while result:
        tail = (result.pop(), tail)
    return tail


Path = collections.namedtuple('Path', 'left right parent_nodes parent_path changed')


class NodeSequence(list):
    lineno = None
    col_offset = None
    def children(self):
        return tuple(self)
    def make_node(self, linked_list):
        return type(self)(*iterate(linked_list))


class Zipper(_ObjectProxy):
    __slots__ = ('path')

    def __init__(self, focus, path=None):
        # Call ObjectProxy.__init__ directly to avoid the super call.  
        _ObjectProxy.__init__(self, focus)
        self._self_path = path

    def left(self):
        if self._self_path and self._self_path.left:
            focus, left = self._self_path.left
            path = self._self_path._replace(left=left,
                                            right=(self.__wrapped__,
                                                   self._self_path.right))
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
            path = self._self_path._replace(left=concatenate(siblings, (self.__wrapped__, self._self_path.left)),
                                            right=())
            return type(self)(focus=focus, path=path)

    def down(self):
        try:
            children = self.__wrapped__.get_children()
            first = next(children)
        except StopIteration:
            return
        path = Path(
            left=None,
            right=linked_list(*children),
            parent_nodes=(self.__wrapped__, self._self_path.parent_nodes) if self._self_path else (self.__wrapped__, None),
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

    # Specialized traversal functions
    def next_statement(self):
        location = self
        while not location.is_statement:
            location = location.up()
        return location.right()

    def previous_statement(self):
        location = self
        while not location.is_statement:
            location = location.up()
        return location.left()

    def nodes_of_class(self, cls, skip_class=None):
        """return an iterator on nodes which are instance of the given class(es)

        cls may be a class object or a tuple of class objects
        """
        if isinstance(self, cls):
            yield self
        child = self.down()
        while child:
            if skip_class is not None and isinstance(location, skip_class):
                continue
            for matching in child.nodes_of_class(cls, skip_class):
                yield matching
            child = child.right()
            if isinstance(child, collections.Sequence):
                child = child.down()

    def nearest(self, nodes):
        """return the node which is the nearest before this one in the
        given list of nodes
        """
        myroot = self.root()
        mylineno = self.fromlineno
        nearest = None, 0
        for node in nodes:
            assert node.root() is myroot, \
                   'nodes %s and %s are not from the same AST' % (self, node)
            lineno = node.fromlineno
            if node.fromlineno > mylineno:
                break
            if lineno > nearest[1]:
                nearest = node, lineno
        # FIXME: raise an exception if nearest is None ?
        return nearest[0]
    
    # Legacy APIs
    @property
    def parent(self):
        location = self.up()
        if isinstance(self, collections.Sequence):
            return location.up()
        else:
            return location

    def last_child(self):
        return self.rightmost()

    def next_sibling(self):
        return self.next_statement()

    def previous_sibling(self):
        return self.previous_statement()

    def child_sequence(self, child):
        return self.locate_child(child)[1]

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

    def locate_child(self, child):
        """return a 2-uple (child attribute name, sequence or node)"""
        location = self.down()
        index = 0
        while location:
            if location is child:
                return self._astroid_fields[index], location
            if (isinstance(location, collections.Sequence)
                and child in location):
                return self._astroid_fields[index], location
            index += 1
        msg = 'Could not find %s in %s\'s children'
        raise exceptions.AstroidError(msg % (repr(child), repr(self)))
    # FIXME : should we merge child_sequence and locate_child ? locate_child
    # is only used in are_exclusive, child_sequence one time in pylint.

    # Editing
    def replace(self, focus):
        return type(self)(focus=focus, path=self._self_path._replace(changed=True))

    def edit(self, *args, **kws):
        return type(self)(focus=self.__wrapped__.make_focus(*args, **kws),
                          path=self._self_path._replace(changed=True))
