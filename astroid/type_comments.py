"""Inject type_comments into the AST."""
import collections
import re
import tokenize

from six import StringIO

from astroid import nodes

TYPE_ANNOTATION = re.compile(r'#\s*type:\s*(.*)')  # # type:
IGNORE = re.compile(r'\s*ignore\b')
FUNCTION_ANNOTATION = re.compile(r'(\(.*\))\s*->\s*(.*)')
STAR_ARGS = re.compile(r'([(,]\s*)\*{1,2}')  # "(*Any" or "... , *Any" or "... , **Any" or
EMPTY_ARGS = re.compile(r'\(\s*\)')  # ( any-whitespace )
UNTYPED_ELLIPSIS_ARGS = re.compile(r'\(\s*\.{3}\s*\)')  # ( any-whitespace ... any-whitespace )
COMPLEX_NAME = re.compile(r".*[,(\[]")

TypeComment = collections.namedtuple('TypeComment', 'arg, vararg, kwarg, returns')

def extract_type_comment(comment):
    # type: (str) -> Optional[TypeComment]
    """Return a TypeComment if this is a `# type:` comment"""

    # Skip if the comment does not start with '# type:'.
    m = TYPE_ANNOTATION.match(comment)
    if not m:
        return None
    expr = m.group(1)  # Everything after '# type:'

    # Skip if it's "# type: ignore"
    if IGNORE.match(expr):
        return None

    expr = expr.split("#")[0].strip()
    # Does it look like a signature annotation?
    m = FUNCTION_ANNOTATION.match(expr)
    if m:
        arg_types, return_type = m.groups()
        if EMPTY_ARGS.match(arg_types) or UNTYPED_ELLIPSIS_ARGS.match(expr):
            # `...` is not valid Python 2 syntax, so just return the return_type.
            ret = TypeComment(None, None, None, return_type)
        else:
            rest, _, kwarg = arg_types.strip(" ()").partition("**")
            rest, _, vararg = rest.strip(" ,").partition("*")
            args = rest.strip(" ,")

            ret = TypeComment(
                ("(%s,)" % args) if args else "()",
                vararg,
                kwarg,
                return_type
            )
    else:
        ret = TypeComment(expr, None, None, None)

    # Skip if expr can't be parsed using compile().
    for expr in ret:
        try:
            if expr:
                compile(expr, '<string>', 'eval')
        except Exception:
            return None

    return ret

def get_scope_map(module):
    """Return a dictionary of line number to scopes for quick lookups."""
    def recurse(node, scope_map):
        if isinstance(node, nodes.FunctionDef):
            # For functions we look until the first item in the body.
            # Sadly the docstring doesn't count in the body so it's not perfect.
            if node.body:
                tolineno = node.body[0].fromlineno
            else:
                # For functions without bodies (so just a docstring) we just sort of take the 2 lines after the start.
                tolineno = node.blockstart_tolineno + 3
            for line in range(node.fromlineno, tolineno):
                scope_map[line] = node
        elif isinstance(node, (nodes.Assign, nodes.With, nodes.For)):
            for line in range(node.fromlineno, node.tolineno + 1):
                scope_map[line] = node

        for child in node.get_children():
            recurse(child, scope_map)
        return scope_map
    return recurse(module, {})

def inject_type_comments(builder, data, module):
    """Inject type_comments into the module node."""
    if "type:" not in data:
        return

    scope_map = get_scope_map(module)

    def build(token, line, parent):
        """Build an astroid node from token at lineno"""
        # For performance reasons try to create NodeNG objects directly.
        if token == 'None':
            return nodes.Const(None, line, parent=parent)
        elif COMPLEX_NAME.match(token) is None:
            return nodes.Name(token, line, parent=parent)
        else:
            # This is faster than using extract_node.
            ret = builder.string_build("\n" * (line - 1) + token).body[0].value
            ret.parent = parent
            return ret

    # Tokenize the file looking for those juicy # type: annotations.
    tokens = tokenize.generate_tokens(StringIO(data).readline)
    last_name = None
    for tok_type, tok_val, (lineno, _), _, _ in tokens:
        if tok_type == tokenize.NAME:
            # Save this name for parsing *arg and **kwarg type comments. See below.
            last_name = tok_val
        elif tok_type == tokenize.COMMENT:
            type_comment = extract_type_comment(tok_val)
            if type_comment:
                target = scope_map[lineno]
                if not target:
                    continue

                arg, vararg, kwarg, returns = type_comment
                if not returns:
                    # This is a "type: arg" comment
                    assert vararg is None
                    assert kwarg is None

                    annotation = build(arg, lineno, target)
                    if isinstance(target, nodes.FunctionDef):
                        for i, argument in enumerate(target.args.args):
                            if target.args.args[i].lineno == lineno:
                                target.args.annotations[i] = annotation
                                break
                        else:
                            # Sadly, vararg and kwarg lose their line numbers in the AST.
                            # So we'll use the last_name to figure out which argument this
                            # might be.
                            if last_name == target.args.vararg:
                                target.args.varargannotation = annotation
                            elif last_name == target.args.kwarg:
                                target.args.kwargannotation = annotation
                    elif isinstance(target, (nodes.Assign, nodes.With, nodes.For)):
                        target.type_comment = annotation
                else:
                    # This is a "(arg, *vararg, *kwarg) -> returns" comment
                    if isinstance(target, nodes.FunctionDef):
                        if arg:
                            # Arg will always be a tuple of arguments.
                            annotations = build(arg, lineno, target).elts

                            if len(annotations) == len(target.args.annotations):
                                start = 0
                            elif len(annotations) == len(target.args.annotations) - 1:
                                # XXX: Check if it could be a method, self.is_method() is pretty expensive
                                # In methods you're allowed to not type `self`.
                                start = 1
                            else:
                                raise Exception("Mismatch in args")

                            for i, elt in enumerate(annotations):
                                target.args.annotations[i + start] = elt

                        if vararg:
                            target.args.varargannotation = build(vararg, lineno, target)

                        if kwarg:
                            target.args.kwargannotation = build(kwarg, lineno, target)

                        target.returns = build(returns, lineno, target)
