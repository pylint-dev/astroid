import collections
import itertools
import pprint
import os
import unittest

import hypothesis
from hypothesis import strategies

import astroid
from astroid.tree import zipper


# This screens out the empty init files.
astroid_file = strategies.sampled_from(os.path.join(p, n) for p, _, ns in os.walk('astroid/') for n in ns if n.endswith('.py') and '__init__.py' not in n)

MapNode = collections.namedtuple('MapNode', 'children parent moves')

def ast_from_file_name(name):
    with open(name, 'r') as source_file:
        print(name)
        root = astroid.parse(source_file.read())
        to_visit = [(root, None)]
        ast = {}
        while to_visit:
            node, parent = to_visit.pop()
            children = tuple(iter(node)) if node else ()
            to_visit.extend((c, node) for c in children)
            moves = []
            if children:
                moves.append(zipper.Zipper.down)
            if parent:
                moves.append(zipper.Zipper.up)
                index = ast[id(parent)].children.index(node)
                if index > 0:
                    moves.append(zipper.Zipper.left)
                if index < len(ast[id(parent)].children) - 1:
                    moves.append(zipper.Zipper.right)
            ast[id(node)] = MapNode(children, parent, tuple(moves))
    return ast, root

ast_strategy = strategies.builds(ast_from_file_name, astroid_file)

# pprint.pprint(ast_strategy.example())

class TestZipper(unittest.TestCase):
    @hypothesis.settings(perform_health_check=False)
    @hypothesis.given(ast_strategy, strategies.integers(min_value=0, max_value=100), strategies.choices())
    def test(self, ast_root, length, choice):
        ast, root = ast_root
        old_position = zipper.Zipper(root)
        for _ in range(length):
            move = choice(ast[id(old_position.__wrapped__)].moves)
            new_position = move(old_position)
            if move is zipper.Zipper.down:
                assert(new_position.__wrapped__ is next(iter(old_position)))
            if move is zipper.Zipper.up:
                assert(new_position.__wrapped__ is ast[id(old_position.__wrapped__)].parent)
            if move is zipper.Zipper.left or move is zipper.Zipper.right:
                parent = ast[id(old_position.__wrapped__)].parent
                siblings = ast[id(parent)].children
                index = siblings.index(old_position.__wrapped__)
                if move is zipper.Zipper.left:
                    assert(new_position.__wrapped__ is siblings[index - 1])
                if move is zipper.Zipper.right:
                    assert(new_position.__wrapped__ is siblings[index + 1])
            old_position = new_position

if __name__ == '__main__':
    unittest.main()
