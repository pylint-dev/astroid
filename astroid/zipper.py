import collections

import wrapt


def linked_list(*values, **kws):
    if values:
        tail = (values[-1], kws.get('tail', None))
        for value in reversed(values[:-1]):
            tail = (value, tail)
        return tail
    else:
        return None

def reverse(linked_list):
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
    node = linked_list
    while node is not None:
        yield node[0]
        node = node[1]

def concatenate(left, right):
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

Path = collections.namedtuple('Path', 'left right parent_nodes parent_path changed')

# Because every zipper method creates a new zipper, zipper creation
# has to be optimized as much as possible.  Using wrapt here instead
# of lazy_object_proxy avoids several additional function calls every
# time an AST node method has to be accessed through a new zipper.
class Zipper(wrapt.ObjectProxy):
    __slots__ = ('_path')

    def __init__(cls, node, path=None):
        # This inlines the proxy's __init__ to avoid the extra Python
        # function call.  wrapt has additional code to proxy
        # __qualname__ in __init__, elided here to save time, and
        # __qualname__ will thus not be proxied.
        object.__setattr__(self, '__wrapped__', node)
        object.__setattr__(self, '_path', path)

    def left(self):
        if self._path and self._path.left:
            node, left = self._path.left
            path = self._path._replace(left=left,
                                      right=(self.__wrapped__, self._path.right))
           return type(self)(node=node, path=path)

    def right(self):
        if self._path and self._path.right:
            node, right = self._path.right
            path = self._path._replace(left=(self.__wrapped__, self._path.left),
                                      right=right)
            return type(self)(node=node, path=path)

    def down(self):
        children = getattr(self.__wrapped__, 'children', None)
        if children:
            path = Path(
                left=None,
                right=linked_list(*children[1:]),
                parent_nodes=(self.__wrapped__, self._path.parent_nodes) if self._path else (self.__wrapped__, None),
                parent_path=self._path,
                changed=False)
            return type(self)(node=children[0], path=path)

    def up(self):
        if self._path:
            left, right, parent_nodes, parent_path, changed = self._path
            if parent_nodes:
                node = parent_nodes[0]
                if changed:
                    return type(self)(
                        node=node.make_node(*iterate(concatenate(reverse(left), (self.__wrapped__, right)))),
                        path=parent_path and parent_path._replace(changed=True))
                else:
                    return type(self)(node=node, path=parent_path)

    def last_child(self):
        if self._path and self._path.right:
            siblings, node = self._path.right[:-1], self._path.right[-1]
            path = self._path._replace(left=self._path.left + (self.__wrapped__,)
                                       + siblings,
                                       right=())
            return type(self)(node, path)

    @property
    def parent(self):
        return self.up()

    def root(self):
        """return the root node of the tree"""
        location = self
        while location._path:
            location = location.up()
        return location

    def next_sibling(self):
        """return the next sibling"""
        siblings = self.up().child_sequence(self.__wrapped__)
        index = siblings.index(self.__wrapped__)
        try:
            return type(self)(siblings[index + 1])
        except IndexError:
            pass

    def previous_sibling(self):
        """return the previous sibling"""
        siblings = self.up().child_sequence(self.__wrapped__)
        index = siblings.index(self.__wrapped__)
        if index >= 1:
            return type(self)(siblings[index - 1])

    def replace(self, node):
        return type(self)(node=node, path=self._path._replace(changed=True))

    def edit(self, *args, **kws):
        return type(self)(node=self.__wrapped__.make_node(*args, **kws),
                          path=self._path._replace(changed=True))
