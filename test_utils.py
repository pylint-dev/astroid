"""Utility functions for test code that uses astroid ASTs as input."""
import textwrap

from astroid import nodes
from astroid import builder

# The name of the transient function that is used to
# wrap expressions to be extracted when calling
# extract_node.
_TRANSIENT_FUNCTION = '__'

# The comment used to select a statement to be extracted
# when calling extract_node.
_STATEMENT_SELECTOR = '#@'


def _extract_expression(node):
    """Find an expression in a call to _TRANSIENT_FUNCTION and extract it.

    The function walks the AST recursively to search for an expression that
    is wrapped into a call to _TRANSIENT_FUNCTION. If it finds such an
    expression, it completely removes the function call node from the tree,
    replacing it by the wrapped expression inside the parent.

    :param node: An astroid node.
    :type node:  astroid.bases.NodeNG
    :returns: The wrapped expression on the modified tree, or None if no such
    expression can be found.
    :rtype:  astroid.bases.NodeNG or None
    """
    if (isinstance(node, nodes.CallFunc)
        and isinstance(node.func, nodes.Name)
        and node.func.name == _TRANSIENT_FUNCTION):
        real_expr = node.args[0]
        real_expr.parent = node.parent
        # Search for node in all _astng_fields (the fields checked when
        # get_children is called) of its parent. Some of those fields may
        # be lists or tuples, in which case the elements need to be checked.
        # When we find it, replace it by real_expr, so that the AST looks
        # like no call to _TRANSIENT_FUNCTION ever took place.
        for name in node.parent._astng_fields:
            child = getattr(node.parent, name)
            if isinstance(child, (list, tuple)):
                for idx, compound_child in enumerate(child):
                    if compound_child is node:
                        child[idx] = real_expr
            elif child is node:
                setattr(node.parent, name, real_expr)
        return real_expr
    else:
        for child in node.get_children():
            result = _extract_expression(child)
            if result:
                return result


def _find_statement_by_line(node, line):
    """Extracts the statement on a specific line from an AST.

    If the line number of node matches line, it will be returned;
    otherwise its children are iterated and the function is called
    recursively.

    :param node: An astroid node.
    :type node: astroid.bases.NodeNG
    :param line: The line number of the statement to extract.
    :type line: int
    :returns: The statement on the line, or None if no statement for the line
      can be found.
    :rtype:  astroid.bases.NodeNG or None
    """
    if isinstance(node, (nodes.Class, nodes.Function)):
        # This is an inaccuracy in the AST: the nodes that can be
        # decorated do not carry explicit information on which line
        # the actual definition (class/def), but .fromline seems to
        # be close enough.
        node_line = node.fromlineno
    else:
        node_line = node.lineno

    if node_line == line:
        return node

    for child in node.get_children():
        result = _find_statement_by_line(child, line)
        if result:
            return result

    return None

def extract_node(code, module_name=''):
    """Parses some Python code as a module and extracts a designated AST node.

    Statements:
     To extract a statement node, append #@ to the end of the line

     Examples:
       >>> def x():
       >>>   def y():
       >>>     return 1 #@

       The return statement will be extracted.

       >>> class X(object):
       >>>   def meth(self): #@
       >>>     pass

      The funcion object 'meth' will be extracted.

    Expression:
     To extract an arbitrary expression, surround it with the fake
     function call __(...). After parsing, the surrounded expression
     will be returned and the whole AST (accessible via the returned
     node's parent attribute) will look like the function call was
     never there in the first place.

     Examples:
       >>> a = __(1)

       The const node will be extracted.

       >>> def x(d=__(foo.bar)): pass

       The node containing the default argument will be extracted.

       >>> def foo(a, b):
       >>>   return 0 < __(len(a)) < b

       The node containing the function call 'len' will be extracted.

    If no statement or expression is selected, the last toplevel
    statement will be returned.

    If the selected is a discard statement, (i.e. an expression turned
    into a statement), the wrapped expression is returned instead.

    :param str code: A piece of Python code that is parsed as
    a module. Will be passed through textwrap.dedent first.
    :param str module_name: The name of the module.
    :returns: The designated node from the parse tree.
    :rtype: astroid.bases.NodeNG
    """
    requested_line = None
    for idx, line in enumerate(code.splitlines()):
        if line.strip().endswith(_STATEMENT_SELECTOR):
            requested_line = idx + 1
            break

    tree = build_module(code, module_name=module_name)
    if requested_line:
        node = _find_statement_by_line(tree, requested_line)
    else:
        node = _extract_expression(tree)

    if not node:
        node = tree.body[-1]

    if isinstance(node, nodes.Discard):
        return node.value
    else:
        return node


def build_module(code, module_name=''):
    """Parses a string module with a builder.
    :param code: The code for the module.
    :type code: str
    :param module_name: The name for the module
    :type module_name: str
    :returns: The module AST.
    :rtype:  astroid.bases.NodeNG
    """
    code = textwrap.dedent(code)
    return builder.AstroidBuilder(None).string_build(code, modname=module_name)
