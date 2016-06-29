# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""The AstroidBuilder makes astroid from living object and / or from _ast

The builder is not thread safe and can't be used to parse different sources
at the same time.
"""

import ast
import os
import sys
import textwrap

from astroid import exceptions
from astroid.interpreter import assign
from astroid.interpreter import runtimeabc
from astroid import manager
from astroid import modutils
from astroid.tree import rebuilder
from astroid.tree import treeabc
from astroid import util

raw_building = util.lazy_import('raw_building')
nodes = util.lazy_import('nodes')


def _parse(string):
    return compile(string, "<string>", 'exec', ast.PyCF_ONLY_AST)


if sys.version_info >= (3, 0):
    # pylint: disable=no-name-in-module; We don't understand flows yet.
    from tokenize import detect_encoding

    def open_source_file(filename):
        with open(filename, 'rb') as byte_stream:
            encoding = detect_encoding(byte_stream.readline)[0]
        stream = open(filename, 'r', newline=None, encoding=encoding)
        data = stream.read()
        return stream, encoding, data

else:
    import re

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


class AstroidBuilder(object):

    """Class for building an astroid tree from source code or from a live module.

    The param *manager* specifies the manager class which should be used.
    If no manager is given, then the default one will be used. The
    param *apply_transforms* determines if the transforms should be
    applied after the tree was built from source or from a live object,
    by default being True.
    """

    def __init__(self, manager=None, apply_transforms=True):
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
            node = raw_building.ast_from_object(module, name=modname)
            # FIXME
            node.source_file = path
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
                'Wrong ({encoding}) or no encoding specified for {filename}.',
                encoding=encoding, filename=path))
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
        module.source_code = data.encode('utf-8')
        return self._post_build(module, 'utf-8')

    def _post_build(self, module, encoding):
        """Handles encoding and delayed nodes after a module has been built"""
        module.file_encoding = encoding
        self._manager.cache_module(module)

        # Visit the transforms
        if self._apply_transforms:
            module = self._manager.visit_transforms(module)
        delayed_assignments(module)
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
            package = path and path.find('__init__.py') > -1 or False
        builder = rebuilder.TreeRebuilder()
        module = builder.visit_module(node, modname, node_file, package)
        return module


def delayed_assignments(root):
    '''This function modifies nodes according to AssignAttr nodes.

    It traverses the entire AST, and when it encounters an AssignAttr
    node it modifies the instance_attrs or external_attrs of the node
    respresenting that object.  Because it uses inference functions
    that in turn depend on instance_attrs and external_attrs, calling
    it a tree that already have instance_attrs and external_attrs set
    may crash or fail to modify those variables correctly.

    Args:
        root (node_classes.NodeNG): The root of the AST that 
            delayed_assignments() is searching for assignments.

    '''
    stack = [root]
    while stack:
        node = stack.pop()
        stack.extend(node.get_children())
        if isinstance(node, treeabc.AssignAttr):
            frame = node.frame()
            try:
                # Here, node.expr.infer() will return either the node
                # being assigned to itself, for Module, ClassDef,
                # FunctionDef, or Lambda nodes, or an Instance object
                # corresponding to a ClassDef node.
                for inferred in node.expr.infer():
                    if isinstance(inferred, runtimeabc.Instance):
                        values = inferred._proxied.instance_attrs[node.attrname]
                    elif isinstance(inferred, treeabc.Lambda):
                        values = inferred.instance_attrs[node.attrname]
                    elif isinstance(inferred, (treeabc.Module, treeabc.ClassDef)):
                        values = inferred.external_attrs[node.attrname]
                    else:
                        continue
                    if node in values:
                        continue
                    elif not assign.can_assign(inferred, node.attrname):
                        continue
                    else:
                        # I have no idea why there's a special case
                        # for __init__ that changes the order of the
                        # attributes or what that order means.
                        if (values and frame.name == '__init__' and not
                            values[0].frame().name == '__init__'):
                            values.insert(0, node)
                        else:
                            values.append(node)
            except (exceptions.InferenceError, exceptions.AstroidBuildingError):
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


# The name of the transient function that is used to
# wrap expressions to be extracted when calling
# extract_node.
_TRANSIENT_FUNCTION = '__'

# The comment used to select a statement to be extracted
# when calling extract_node.
_STATEMENT_SELECTOR = '#@'

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
    if (isinstance(node, treeabc.Call)
            and isinstance(node.func, treeabc.Name)
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

                    # Can't find a cleaner way to do this.
                    if isinstance(compound_child, treeabc.Parameter):
                        if compound_child.default is node:
                            child[idx].default = real_expr
                        elif compound_child.annotation is node:
                            child[idx].annotation = real_expr
                        else:
                            child[idx] = real_expr
                    elif compound_child is node:
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
    if isinstance(node, (treeabc.ClassDef, treeabc.FunctionDef)):
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

      The funcion object 'meth' will be extracted.

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
        if isinstance(node, treeabc.Expr):
            return node.value
        else:
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
    else:
        return extracted
