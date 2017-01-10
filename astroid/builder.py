# Copyright (c) 2006-2011, 2013-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014-2015 Google, Inc.
# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015-2016 Cara Vinson <ceridwenv@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""The AstroidBuilder makes astroid from living object and / or from _ast

The builder is not thread safe and can't be used to parse different sources
at the same time.
"""

import re
import os
import sys
import textwrap
import _ast

import collections
from six import StringIO

from astroid import bases
from astroid import exceptions
from astroid import manager
from astroid import modutils
from astroid import raw_building
from astroid import rebuilder
from astroid import nodes
from astroid import util

# The name of the transient function that is used to
# wrap expressions to be extracted when calling
# extract_node.
_TRANSIENT_FUNCTION = '__'

# The comment used to select a statement to be extracted
# when calling extract_node.
_STATEMENT_SELECTOR = '#@'


def _parse(string):
    return compile(string, "<string>", 'exec', _ast.PyCF_ONLY_AST)

TYPE_ANNOTATION = re.compile(r'#\s*type:\s*(.*)')  # # type:
IGNORE = re.compile(r'\s*ignore\b')
FUNCTION_ANNOTATION = re.compile(r'(\(.*\))\s*->\s*(.*)')
STAR_ARGS = re.compile(r'([(,]\s*)\*{1,2}')  # "(*Any" or "... , *Any" or "... , **Any" or
EMPTY_ARGS = re.compile(r'\(\s*\)')  # ( any-whitespace )
UNTYPED_ELLIPSIS_ARGS = re.compile(r'\(\s*\.{3}\s*\)')  # ( any-whitespace ... any-whitespace )

TypeComment = collections.namedtuple('TypeComment', 'arg, vararg, kwarg, returns')

def expr_for_comment(comment):
    # type: (str) -> Optional[TypeComment]
    """Return a compilable string to represent a type annotation."""

    # Skip if the comment does not start with '# type:'.
    m = TYPE_ANNOTATION.match(comment)
    if not m:
        return None
    expr = m.group(1)  # Everything after '# type:'

    # Skip if it's "# type: ignore"
    if IGNORE.match(expr):
        return None

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
        except Exception as e:
            return None

    return ret

def fill_scope_map(scope_map, node):
    # type: (List[NodeNG], NodeNG) -> None
    """Fill in the scope_map so that we get a quick lookup table of line numbers to scopes."""

    if isinstance(node, nodes.FunctionDef):
        for line in range(node.fromlineno, node.body[0].fromlineno + 2):
            scope_map[line] = node
    elif isinstance(node, (nodes.Assign, nodes.With, nodes.For)):
        # We want our line numbers to be 1 indexed, however fromlineno and to lineno
        # are 0 indexed so add 1, except fromlineno always starts one line after the
        # def or class so just don't add 1 to that one.
        for line in range(node.fromlineno, node.tolineno + 1):
            scope_map[line] = node
    for child in node.get_children():
        fill_scope_map(scope_map, child)

def inject_imports(data, module):
    if not re.search(r'#\s*type:', data):
        return

    # Build a scope_map for faster lookups.
    scope_map = [None] * (data.count("\n") + 2)
    fill_scope_map(scope_map, module)

    # Tokenize the file looking for those juicy # type: annotations.
    import tokenize

    module.injected_lines = []
    tokens = tokenize.generate_tokens(StringIO(data).readline)
    last_token = None
    for tok_type, tok_val, (lineno, _), _, _ in tokens:
        if tok_type == tokenize.COMMENT:
            expr = expr_for_comment(tok_val)
            if expr:
                scope = scope_map[lineno]
                if not scope:
                    continue

                arg, vararg, kwarg, returns = expr
                if not returns:
                    # This is a "type: arg" comment
                    assert vararg is None
                    assert kwarg is None

                    annotation = extract_node("\n" * (lineno-1) + arg)
                    if isinstance(scope, nodes.FunctionDef):
                        for i, argument in enumerate(scope.args.args):
                            if scope.args.args[i].lineno == lineno:
                                annotation.parent = scope
                                scope.args.annotations[i] = annotation
                                break
                        else:
                            # Sadly, vararg and kwarg lose their line numbers.
                            # So we'll use the last_name to approximate where we are
                            if last_token == scope.args.vararg:
                                annotation.parent = scope
                                scope.args.varargannotation = annotation
                            elif last_token == scope.args.kwarg:
                                annotation.parent = scope
                                scope.args.kwargannotation = annotation
                    elif isinstance(scope, (nodes.Assign, nodes.With, nodes.For)):
                        annotation.parent = scope
                        scope.type_comment = annotation
                else:
                    # This is a "(arg, *vararg, *kwarg) -> returns" comment
                    if isinstance(scope, nodes.FunctionDef):
                        try:
                            if arg:
                                annotations = extract_node("\n" * (lineno-1) + arg).elts

                                if len(annotations) == len(scope.args.annotations):
                                    start = 0
                                elif scope.is_method() and len(annotations) == len(scope.args.annotations) - 1:
                                    # In methods you're allowed to not type `self`.
                                    start = 1
                                else:
                                    raise Exception("Mismatch in args")

                                for i, elt in enumerate(annotations):
                                    elt.parent = scope
                                    scope.args.annotations[i + start] = elt

                            if vararg:
                                varargannotation = extract_node("\n" * (lineno-1) + vararg)
                                varargannotation.parent = scope
                                scope.args.varargannotation = varargannotation

                            if kwarg:
                                kwargannotation = extract_node("\n" * (lineno - 1) + kwarg)
                                kwargannotation.parent = scope
                                scope.args.kwargannotation = kwargannotation

                            return_type = extract_node("\n" * (lineno-1) + returns)
                            return_type.parent = scope
                            scope.returns = return_type
                        except Exception:
                            import pdb; pdb.set_trace()
                            raise

        if tok_type == tokenize.NAME:
            last_token = tok_val

    return module

if sys.version_info >= (3, 0):
    from tokenize import detect_encoding

    def open_source_file(filename):
        with open(filename, 'rb') as byte_stream:
            encoding = detect_encoding(byte_stream.readline)[0]
        stream = open(filename, 'r', newline=None, encoding=encoding)
        data = stream.read()
        return stream, encoding, data

else:
    _ENCODING_RGX = re.compile(r"\s*#+.*coding[:=]\s*([-\w.]+)")

    def _guess_encoding(string):
        """get encoding from a python file as string or return None if not found"""
        # check for UTF-8 byte-order mark
        if string.startswith('\xef\xbb\xbf'):
            return 'UTF-8'
        for line in string.split('\n', 2)[:2]:
            # check for encoding declaration
            match = _ENCODING_RGX.match(line)
            if match is not None:
                return match.group(1)

    def open_source_file(filename):
        """get data for parsing a file"""
        stream = open(filename, 'U')
        data = stream.read()
        encoding = _guess_encoding(data)
        return stream, encoding, data


MANAGER = manager.AstroidManager()


def _can_assign_attr(node, attrname):
    try:
        slots = node.slots()
    except NotImplementedError:
        pass
    else:
        if slots and attrname not in set(slot.value for slot in slots):
            return False
    return True


class AstroidBuilder(raw_building.InspectBuilder):
    """Class for building an astroid tree from source code or from a live module.

    The param *manager* specifies the manager class which should be used.
    If no manager is given, then the default one will be used. The
    param *apply_transforms* determines if the transforms should be
    applied after the tree was built from source or from a live object,
    by default being True.
    """
    # pylint: disable=redefined-outer-name
    def __init__(self, manager=None, apply_transforms=True):
        super(AstroidBuilder, self).__init__()
        self._manager = manager or MANAGER
        self._apply_transforms = apply_transforms

    def module_build(self, module, modname=None):
        """Build an astroid from a living module instance."""
        node = None
        path = getattr(module, '__file__', None)
        if path is not None:
            path_, ext = os.path.splitext(modutils._path_from_filename(path))
            if ext in ('.py', '.pyc', '.pyo') and os.path.exists(path_ + '.py'):
                node = self.file_build(path_ + '.py', modname)
        if node is None:
            # this is a built-in module
            # get a partial representation by introspection
            node = self.inspect_build(module, modname=modname, path=path)
            if self._apply_transforms:
                # We have to handle transformation by ourselves since the
                # rebuilder isn't called for builtin nodes
                node = self._manager.visit_transforms(node)
        return node

    def file_build(self, path, modname=None):
        """Build astroid from a source code file (i.e. from an ast)

        *path* is expected to be a python source file
        """
        try:
            stream, encoding, data = open_source_file(path)
        except IOError as exc:
            util.reraise(exceptions.AstroidBuildingError(
                'Unable to load file {path}:\n{error}',
                modname=modname, path=path, error=exc))
        except (SyntaxError, LookupError) as exc:
            util.reraise(exceptions.AstroidSyntaxError(
                'Python 3 encoding specification error or unknown encoding:\n'
                '{error}', modname=modname, path=path, error=exc))
        except UnicodeError:  # wrong encoding
            # detect_encoding returns utf-8 if no encoding specified
            util.reraise(exceptions.AstroidBuildingError(
                'Wrong or no encoding specified for {filename}.',
                filename=path))
        with stream:
            # get module name if necessary
            if modname is None:
                try:
                    modname = '.'.join(modutils.modpath_from_file(path))
                except ImportError:
                    modname = os.path.splitext(os.path.basename(path))[0]
            # build astroid representation
            module = self._data_build(data, modname, path)
            return self._post_build(module, encoding)

    def string_build(self, data, modname='', path=None):
        """Build astroid from source code string."""
        module = self._data_build(data, modname, path)
        module.file_bytes = data.encode('utf-8')
        return self._post_build(module, 'utf-8')

    def _post_build(self, module, encoding):
        """Handles encoding and delayed nodes after a module has been built"""
        module.file_encoding = encoding
        self._manager.cache_module(module)
        # post tree building steps after we stored the module in the cache:
        for from_node in module._import_from_nodes:
            if from_node.modname == '__future__':
                for symbol, _ in from_node.names:
                    module.future_imports.add(symbol)
            self.add_from_names_to_locals(from_node)
        # handle delayed assattr nodes
        for delayed in module._delayed_assattr:
            self.delayed_assattr(delayed)

        # Visit the transforms
        if self._apply_transforms:
            module = self._manager.visit_transforms(module)
        return module

    def _data_build(self, data, modname, path):
        """Build tree node from data and add some informations"""
        try:
            node = _parse(data + '\n')
        except (TypeError, ValueError, SyntaxError) as exc:
            util.reraise(exceptions.AstroidSyntaxError(
                'Parsing Python code failed:\n{error}',
                source=data, modname=modname, path=path, error=exc))
        if path is not None:
            node_file = os.path.abspath(path)
        else:
            node_file = '<?>'
        if modname.endswith('.__init__'):
            modname = modname[:-9]
            package = True
        else:
            package = path.find('__init__.py') > -1 if path else False
        builder = rebuilder.TreeRebuilder(self._manager)
        module = builder.visit_module(node, modname, node_file, package)
        module._import_from_nodes = builder._import_from_nodes
        module._delayed_assattr = builder._delayed_assattr
        inject_imports(data, module)
        return module

    def add_from_names_to_locals(self, node):
        """Store imported names to the locals

        Resort the locals if coming from a delayed node
        """
        _key_func = lambda node: node.fromlineno
        def sort_locals(my_list):
            my_list.sort(key=_key_func)

        for (name, asname) in node.names:
            if name == '*':
                try:
                    imported = node.do_import_module()
                except exceptions.AstroidBuildingError:
                    continue
                for name in imported.public_names():
                    node.parent.set_local(name, node)
                    sort_locals(node.parent.scope().locals[name])
            else:
                node.parent.set_local(asname or name, node)
                sort_locals(node.parent.scope().locals[asname or name])

    def delayed_assattr(self, node):
        """Visit a AssAttr node

        This adds name to locals and handle members definition.
        """
        try:
            frame = node.frame()
            for inferred in node.expr.infer():
                if inferred is util.Uninferable:
                    continue
                try:
                    if inferred.__class__ is bases.Instance:
                        inferred = inferred._proxied
                        iattrs = inferred.instance_attrs
                        if not _can_assign_attr(inferred, node.attrname):
                            continue
                    elif isinstance(inferred, bases.Instance):
                        # Const, Tuple, ... we may be wrong, may be not, but
                        # anyway we don't want to pollute builtin's namespace
                        continue
                    elif inferred.is_function:
                        iattrs = inferred.instance_attrs
                    else:
                        iattrs = inferred.locals
                except AttributeError:
                    # XXX log error
                    continue
                values = iattrs.setdefault(node.attrname, [])
                if node in values:
                    continue
                # get assign in __init__ first XXX useful ?
                if (frame.name == '__init__' and values and
                        values[0].frame().name != '__init__'):
                    values.insert(0, node)
                else:
                    values.append(node)
        except exceptions.InferenceError:
            pass


def build_namespace_package_module(name, path):
    return nodes.Module(name, doc='', path=path, package=True)


def parse(code, module_name='', path=None, apply_transforms=True):
    """Parses a source string in order to obtain an astroid AST from it

    :param str code: The code for the module.
    :param str module_name: The name for the module, if any
    :param str path: The path for the module
    :param bool apply_transforms:
        Apply the transforms for the give code. Use it if you
        don't want the default transforms to be applied.
    """
    code = textwrap.dedent(code)
    builder = AstroidBuilder(manager=MANAGER,
                             apply_transforms=apply_transforms)
    return builder.string_build(code, modname=module_name, path=path)


def _extract_expressions(node):
    """Find expressions in a call to _TRANSIENT_FUNCTION and extract them.

    The function walks the AST recursively to search for expressions that
    are wrapped into a call to _TRANSIENT_FUNCTION. If it finds such an
    expression, it completely removes the function call node from the tree,
    replacing it by the wrapped expression inside the parent.

    :param node: An astroid node.
    :type node:  astroid.bases.NodeNG
    :yields: The sequence of wrapped expressions on the modified tree
    expression can be found.
    """
    if (isinstance(node, nodes.Call)
            and isinstance(node.func, nodes.Name)
            and node.func.name == _TRANSIENT_FUNCTION):
        real_expr = node.args[0]
        real_expr.parent = node.parent
        # Search for node in all _astng_fields (the fields checked when
        # get_children is called) of its parent. Some of those fields may
        # be lists or tuples, in which case the elements need to be checked.
        # When we find it, replace it by real_expr, so that the AST looks
        # like no call to _TRANSIENT_FUNCTION ever took place.
        for name in node.parent._astroid_fields:
            child = getattr(node.parent, name)
            if isinstance(child, (list, tuple)):
                for idx, compound_child in enumerate(child):
                    if compound_child is node:
                        child[idx] = real_expr
            elif child is node:
                setattr(node.parent, name, real_expr)
        yield real_expr
    else:
        for child in node.get_children():
            for result in _extract_expressions(child):
                yield result


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
    if isinstance(node, (nodes.ClassDef, nodes.FunctionDef)):
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
     To extract one or more statement nodes, append #@ to the end of the line

     Examples:
       >>> def x():
       >>>   def y():
       >>>     return 1 #@

       The return statement will be extracted.

       >>> class X(object):
       >>>   def meth(self): #@
       >>>     pass

      The function object 'meth' will be extracted.

    Expressions:
     To extract arbitrary expressions, surround them with the fake
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

    If no statements or expressions are selected, the last toplevel
    statement will be returned.

    If the selected statement is a discard statement, (i.e. an expression
    turned into a statement), the wrapped expression is returned instead.

    For convenience, singleton lists are unpacked.

    :param str code: A piece of Python code that is parsed as
    a module. Will be passed through textwrap.dedent first.
    :param str module_name: The name of the module.
    :returns: The designated node from the parse tree, or a list of nodes.
    :rtype: astroid.bases.NodeNG, or a list of nodes.
    """
    def _extract(node):
        if isinstance(node, nodes.Expr):
            return node.value

        return node

    requested_lines = []
    for idx, line in enumerate(code.splitlines()):
        if line.strip().endswith(_STATEMENT_SELECTOR):
            requested_lines.append(idx + 1)

    tree = parse(code, module_name=module_name)
    extracted = []
    if requested_lines:
        for line in requested_lines:
            extracted.append(_find_statement_by_line(tree, line))

    # Modifies the tree.
    extracted.extend(_extract_expressions(tree))

    if not extracted:
        extracted.append(tree.body[-1])

    extracted = [_extract(node) for node in extracted]
    if len(extracted) == 1:
        return extracted[0]
    return extracted
