import cProfile
import itertools
import os

import hypothesis
from hypothesis import strategies

import astroid
from astroid.tree import zipper


# __init__.py screens out the empty init files, testdata because of
# the deliberately-broken files, and unittests because of #310.
astroid_file = strategies.sampled_from(os.path.join(p, n) for p, _, ns in os.walk('astroid/') for n in ns if n.endswith('.py') and '__init__.py' not in n)

def parse_ast(name):
    with open(name, 'r') as source_file:
        print(name)
        ast = zipper.Zipper(astroid.parse(source_file.read()))
        return (ast.down,)

base_case = strategies.builds(parse_ast, astroid_file)
 
def possible_moves(path):
    # position = path[-1]()
    # previous_position = path[-1].__self__
    # if not len(previous_position):
    #     return ()
    # length = 0
    # # If the zipper produces a position that is not the child of the
    # # previous position, this is a bug and thus should crash.
    # for child in previous_position:
    #     length += 1
    #     if child == position:
    #         index = length
    #         break
    # else:
    #     print(position)
    #     print([repr(c) for c in previous_position])
    #     raise astroid.exceptions.AstroidError(
    #         'Invalid AST: {child!r} is not a child of {parent!r}',
    #         child=position, parent=previous_position) 
    # moves = []
    # if position._self_path:
    #     moves.append(position.up)
    # if length > 0:
    #     moves.append(position.down)
    # if index < length:
    #     moves.append(position.right)
    # if index > 0:
    #     moves.append(position.left)
    position = path[-1]()
    return tuple(m for m in (position.down, position.up, position.left, position.right) if m() is not None)

extend = lambda path_strategy: path_strategy.flatmap(lambda path: strategies.sampled_from(possible_moves(path)).map(lambda move: path + (move,)))

walk_ast = strategies.recursive(base_case, extend)

# print(walk_ast.example())

# cProfile.run('print(walk_ast.example())')

@hypothesis.given(walk_ast)
def test(moves):
    print(moves)
    moves = tuple(reversed(moves))
    visited_positions = {id(moves[0].__self__): moves[0].__self__}
    for move in moves:
        position = move()
        if id(position) in visited_positions:
            assert(position == visited_positions[id(position)])
        visited_positions[id(position)] = position

if __name__ == '__main__':
    test()
    # pass
