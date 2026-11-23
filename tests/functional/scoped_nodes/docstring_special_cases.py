def f1(var: tuple = ()):  # doc_node: 'Hello World'  # doc_node.position: 2:4-2:17
    'Hello World'

# +2: doc_node: 'Hello World'
# +1: doc_node.position: 7:4-7:17
def f2() -> "just some comment with an open bracket(":
    'Hello World'

# +2: doc_node: 'Hello World'
# +1: doc_node.position: 12:4-12:17
def f3() -> "Another comment with a colon: ":
    'Hello World'

def f4():  # doc_node: 'Hello World'  # doc_node.position: 16:4-16:17
    # It should work with comments too
    'Hello World'
