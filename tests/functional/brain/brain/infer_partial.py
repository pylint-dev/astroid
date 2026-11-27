from functools import partial
def test(a, b):
    '''Docstring'''
    return a + b
# +6: func: Call(partial(test, 1))
# +5: func.inferred: PartialFunction(PartialFunction)
# +4: func.inferred.as_string(): \ndef test(a, b):\n    """Docstring"""\n    return a + b
# +3: func.inferred.doc_node: 'Docstring'
# +2: func.inferred.doc_node.value: 'Docstring'
# +1: func.inferred.position: 2:0-4:16
partial(test, 1)(3)
