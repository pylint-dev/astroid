'''Rather than generating a random AST, the zipper tests pick a random
file out of astroid's code and parse it, running tests on the
resulting AST.  The tests create a dict-of-lists graph representation
of the AST by using the recursive structure only, without using the
zipper, with each node labeled by a unique integer, and then compare
the zipper's result with what the zipper should return.

'''
import collections
import os
import unittest

import hypothesis
from hypothesis import strategies

import astroid
from astroid import nodes
from astroid.tree import base
from astroid.tree import zipper


# This is a strategy that generates a random file name, screening out
# the empty init files because they produce 1-element ASTs that aren't
# useful for testing.
astroid_file = strategies.sampled_from(os.path.join(p, n) for p, _, ns in os.walk('astroid/') for n in ns if n.endswith('.py') and '__init__.py' not in n)


class ASTMap(dict):
    '''Hypothesis uses the repr of arguments to a function when printing
    output for failed tests but the ASTs are too large to be legible,
    so this is a simple dict subclass with a shortened repr.

    '''
    def __repr__(self):
        return '{ 1: ' + repr(self[1]) + '...}'

class AssignLabels(object):
    '''Traverses an AST, creating a dict with integer labels representing
    AST nodes.

    The keys of the resulting dictionary contain the actual AST node,
    the labels of its children, and the label of its parent.  The
    labels are assigned starting at 1, for the root, in prefix order.
    This is a replacement for an inner function in ast_from_file_name.
    On Python 3, self.label would instead be a closure variable with
    the nonlocal statement.

    '''
    Node = collections.namedtuple('Node', 'node children parent')    
    def __init__(self):
        self.label = 1
    def __call__(self, labels, node, parent_label=0):
        label = self.label
        self.label += 1
        children = tuple(self(labels, c, label) for c in node)
        labels[label] = self.Node(node, children, parent_label)
        return label


Node = collections.namedtuple('Node', 'node children parent edges')
# Each edge represents a valid zipper method, with move being the
# function corresponding to that method and label corresponding to the
# label of the destination node.
Edge = collections.namedtuple('Edge', 'label move')

AST_CACHE = {}

def ast_from_file_name(name):
    '''Takes a file name and creates a dict-of-lists representation of that AST.

    Each key is a unique integer assigned to a node, the values are
    tuples containing the actual node, the integer labels of the
    children, the label of the parent, and pairs of zipper
    methods/functions with the labels of the corresponding node that
    zipper function will generate when applied at the key's node's
    position.

    '''
    # Generating ASTs is slow right now because it depends on
    # inference, so this caches one AST per file.  Avoiding the global
    # caching ensures that other tests can't mutate these ASTs.
    if name in AST_CACHE:
        return AST_CACHE[name]
    with open(name, 'r') as source_file:
        # print(name)
        root = astroid.parse(source_file.read()).__wrapped__
        ast = ASTMap()
        AssignLabels()(ast, root)
        to_visit = [1]
        while to_visit:
            label = to_visit.pop()
            children = ast[label].children
            parent = ast[label].parent
            to_visit.extend(c for c in reversed(children))
            edges = []
            if children:
                edges.append(Edge(children[0], zipper.Zipper.down))
            if parent:
                edges.append(Edge(parent, zipper.Zipper.up))
                edges.append(Edge(1, zipper.Zipper.root))
                siblings = ast[parent].children
                index = siblings.index(label)
                if index > 0:
                    edges.append(Edge(siblings[0], zipper.Zipper.leftmost))
                    edges.append(Edge(siblings[index - 1], zipper.Zipper.left))
                if index < len(siblings) - 1:
                    edges.append(Edge(siblings[index + 1], zipper.Zipper.right))
                    edges.append(Edge(siblings[-1], zipper.Zipper.rightmost))
            ast[label] = Node(ast[label].node, children, parent, tuple(edges))
    AST_CACHE[name] = ast
    return ast

# Buid a strategy that generates digraph representations of ASTs from
# file names.
ast_strategy = strategies.builds(ast_from_file_name, astroid_file)

# These two functions are recursive implementations of preorder and
# postorder traversals that iterate over labels rather than nodes.
# Using recursion reduces the probability of the error being in both
# implementations, the recursive test and the iterative functional
# code.
def preorder_descendants(label, ast, dont_recurse_on=None):
    def _preorder_descendants(label):
        if dont_recurse_on is not None and isinstance(ast[label].node, dont_recurse_on):
            return ()
        else:
            return (label,) + sum((_preorder_descendants(l) for l in ast[label].children), ())
    return (label,) + sum((_preorder_descendants(l) for l in ast[label].children), ())

def postorder_descendants(label, ast, dont_recurse_on=None):
    def _postorder_descendants(label):
        if dont_recurse_on is not None and isinstance(ast[label].node, dont_recurse_on):
            return ()
        else:
            return sum((_postorder_descendants(l) for l in ast[label].children), ()) + (label,)
    return sum((_postorder_descendants(l) for l in ast[label].children), ()) + (label,)

# This test function uses a set-based implementation for finding the
# common parent rather than the reverse-based implementation in the
# actual code.
def common_ancestor(label1, label2, ast):
    ancestors = set()
    while label1:
        if ast[label1].node is not nodes.Empty:
            ancestors.add(label1)
        label1 = ast[label1].parent
    while label2 not in ancestors:
        label2 = ast[label2].parent
    return label2

def traverse_to_node(label, ast, location):
    '''Given a label, a digraph AST, and a starting zipper, traverses the
    zipper to the node for that label.'''
    moves = collections.deque()
    while label != 1:
        siblings = ast[ast[label].parent].children
        index = siblings.index(label)
        moves.extendleft(index * (zipper.Zipper.right,))
        moves.appendleft(zipper.Zipper.down)
        label = ast[label].parent
    for move in moves:
        location = move(location)
    return location

def get_children(label, ast):
    for child_label in ast[label].children:
        if isinstance(ast[child_label].node, collections.Sequence):
            for grandchild_label in ast[child_label].children:
                yield grandchild_label
        else:
            yield child_label

# This function and strategy creates a strategy for generating a
# random node class, for testing that the iterators properly exclude
# nodes of that type and their descendants.
def _all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in _all_subclasses(s)]
node_types_strategy = strategies.sampled_from(_all_subclasses(base.NodeNG))


class TestZipper(unittest.TestCase):
    def check_linked_list(self, linked_list):
        '''Check that this linked list of tuples is correctly formed.'''
        while linked_list:
            self.assertIsInstance(linked_list, tuple)
            self.assertEqual(len(linked_list), 2)
            linked_list = linked_list[1]
        self.assertEqual(len(linked_list), 0)

    def check_zipper(self, position):
        '''Check that a zipper is correctly formed.'''
        self.assertIsInstance(position, (base.NodeNG, collections.Sequence))
        self.assertIsInstance(position._self_path, (zipper.Path, type(None)))
        if position._self_path:
            self.assertIsInstance(position._self_path.parent_path, (zipper.Path, type(None)))
            self.check_linked_list(position._self_path.right)
            self.check_linked_list(position._self_path.left)
            self.check_linked_list(position._self_path.parent_nodes)
            self.assertIsInstance(position._self_path.changed, bool)
    
    @hypothesis.settings(perform_health_check=False)
    @hypothesis.given(ast_strategy, strategies.integers(min_value=0, max_value=100), strategies.choices())
    def test_traversal(self, ast, length, choice):
        hypothesis.note(str(ast[1].node))
        old_label = 1
        old_zipper = zipper.Zipper(ast[1].node)
        for _ in range(length):
            new_label, move = choice(ast[old_label].edges)
            new_zipper = move(old_zipper)
            self.check_zipper(new_zipper)
            hypothesis.note(new_zipper)
            hypothesis.note(ast[new_label].node)
            self.assertIs(new_zipper.__wrapped__, ast[new_label].node)
            old_zipper = new_zipper
            old_label = new_label

    @hypothesis.settings(perform_health_check=False)
    @hypothesis.given(ast_strategy, strategies.choices(), node_types_strategy)
    def test_iterators(self, ast, choice, node_type):
        nodes = tuple(ast)
        random_label = choice(nodes)
        random_node = zipper.Zipper(ast[random_label].node)
        for node, label in zip(random_node.children(), ast[random_label].children):
            self.assertIs(node.__wrapped__, ast[label].node)
        for node, label in zip(random_node.preorder_descendants(), preorder_descendants(random_label, ast)):
            self.assertIs(node.__wrapped__, ast[label].node)
        for node, label in zip(random_node.preorder_descendants(dont_recurse_on=node_type), preorder_descendants(random_label, ast, dont_recurse_on=node_type)):
            self.assertIs(node.__wrapped__, ast[label].node)
        for node, label in zip(random_node.postorder_descendants(), postorder_descendants(random_label, ast)):
            self.assertIs(node.__wrapped__, ast[label].node)
        for node, label in zip(random_node.postorder_descendants(dont_recurse_on=node_type), postorder_descendants(random_label, ast, dont_recurse_on=node_type)):
            self.assertIs(node.__wrapped__, ast[label].node)
        for node, label in zip(random_node.get_children(), get_children(random_label, ast)):
            self.assertIs(node.__wrapped__, ast[label].node)

    @hypothesis.settings(perform_health_check=False)
    @hypothesis.given(ast_strategy, strategies.choices())
    def test_legacy_apis(self, ast, choice):
        root = zipper.Zipper(ast[1].node)
        nodes = tuple(ast)
        random_node = traverse_to_node(choice(nodes), ast, root)
        if random_node.up() is not None:
            if isinstance(random_node.up(), collections.Sequence) and random_node.up().up() is not None:
                self.assertIs(random_node.parent.__wrapped__, random_node.up().up().__wrapped__)
            if isinstance(random_node.up(), base.NodeNG):
                self.assertIs(random_node.parent.__wrapped__, random_node.up().__wrapped__)
        if random_node.right() is not None:
            self.assertIs(random_node.last_child().__wrapped__, random_node.rightmost().__wrapped__)
            self.assertIs(random_node.next_sibling().__wrapped__, random_node.right().__wrapped__)
        if random_node.left() is not None:
            self.assertIs(random_node.previous_sibling().__wrapped__, random_node.left().__wrapped__)

    @hypothesis.settings(perform_health_check=False)
    @hypothesis.given(ast_strategy, ast_strategy, strategies.choices())
    def test_common_parent(self, ast1, ast2, choice):
        hypothesis.assume(ast1 is not ast2)
        root1 = zipper.Zipper(ast1[1].node)
        root2 = zipper.Zipper(ast2[1].node)
        nodes1 = tuple(ast1)[1:]
        nodes2 = tuple(ast2)[1:]
        random_label11 = choice(nodes1)
        random_label12 = choice(nodes1)
        random_label21 = choice(nodes2)
        random_label22 = choice(nodes2)
        random_node11 = traverse_to_node(random_label11, ast1, root1)
        random_node12 = traverse_to_node(random_label12, ast1, root1)
        random_node21 = traverse_to_node(random_label21, ast2, root2)
        random_node22 = traverse_to_node(random_label22, ast2, root2)
        self.assertIs(random_node11.common_ancestor(random_node12).__wrapped__,
                      ast1[common_ancestor(random_label11, random_label12, ast1)].node)
        self.assertIs(random_node21.common_ancestor(random_node22).__wrapped__,
               ast2[common_ancestor(random_label21, random_label22, ast2)].node)
        self.assertIsNone(random_node11.common_ancestor(random_node22))
        self.assertIsNone(random_node12.common_ancestor(random_node21))

if __name__ == '__main__':
    unittest.main()
