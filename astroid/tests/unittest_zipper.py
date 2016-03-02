import collections
import itertools
import pprint
import os
import unittest

import hypothesis
from hypothesis import strategies

import astroid
from astroid.tree import base
from astroid.tree import zipper


# This screens out the empty init files.
astroid_file = strategies.sampled_from(os.path.join(p, n) for p, _, ns in os.walk('astroid/') for n in ns if n.endswith('.py') and '__init__.py' not in n)

class ASTMap(dict):
    def __repr__(self):
        return repr(self[1])

class AssignLabels(object):
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
Edge = collections.namedtuple('Edge', 'label move')

def ast_from_file_name(name):
    with open(name, 'r') as source_file:
        # print(name)
        root = astroid.parse(source_file.read())
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
                siblings = ast[parent].children
                index = siblings.index(label)
                if index > 0:
                    edges.append(Edge(siblings[index - 1], zipper.Zipper.left))
                if index < len(siblings) - 1:
                    edges.append(Edge(siblings[index + 1], zipper.Zipper.right))
            ast[label] = Node(ast[label].node, children, parent, tuple(edges))
    return ast, root

ast_strategy = strategies.builds(ast_from_file_name, astroid_file)

# pprint.pprint(ast_strategy.example())

class TestZipper(unittest.TestCase):
    @hypothesis.settings(perform_health_check=False)
    @hypothesis.given(ast_strategy, strategies.integers(min_value=0, max_value=100), strategies.choices())
    def test(self, ast_root, length, choice):
        ast, root = ast_root
        hypothesis.note(str(root))
        old_label = 1
        old_zipper = zipper.Zipper(root)
        for _ in range(length):
            new_label, move = choice(ast[old_label].edges)
            new_zipper = move(old_zipper)
            hypothesis.note(new_zipper)
            assert(isinstance(new_zipper.__wrapped__,
                              (base.NodeNG, collections.Sequence)))
            assert(new_zipper.__wrapped__ is ast[new_label].node)
            old_zipper = new_zipper
            old_label = new_label

if __name__ == '__main__':
    unittest.main()
