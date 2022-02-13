# Copyright (c) 2006-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2010 Daniel Harding <dharding@gmail.com>
# Copyright (c) 2011, 2013-2015 Google, Inc.
# Copyright (c) 2013-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2013 Phil Schaf <flying-sheep@web.de>
# Copyright (c) 2014 Eevee (Alex Munroe) <amunroe@yelp.com>
# Copyright (c) 2015-2016 Florian Bruhin <me@the-compiler.org>
# Copyright (c) 2015-2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2015 Rene Zhang <rz99@cornell.edu>
# Copyright (c) 2015 Philip Lorenz <philip@bithub.de>
# Copyright (c) 2016-2017 Derek Gustafson <degustaf@gmail.com>
# Copyright (c) 2017-2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2017-2018 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 David Euresti <david@dropbox.com>
# Copyright (c) 2018-2019, 2021 Nick Drozd <nicholasdrozd@gmail.com>
# Copyright (c) 2018 Ville Skyttä <ville.skytta@iki.fi>
# Copyright (c) 2018 Anthony Sottile <asottile@umich.edu>
# Copyright (c) 2018 HoverHell <hoverhell@gmail.com>
# Copyright (c) 2019 Hugo van Kemenade <hugovk@users.noreply.github.com>
# Copyright (c) 2019 Peter de Blanc <peter@standard.ai>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 Peter Kolbus <peter.kolbus@gmail.com>
# Copyright (c) 2020 Tim Martin <tim@asymptotic.co.uk>
# Copyright (c) 2020 Ram Rachum <ram@rachum.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Tushar Sadhwani <86737547+tushar-deepsource@users.noreply.github.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
# Copyright (c) 2021 Daniël van Noord <13665637+DanielNoord@users.noreply.github.com>
# Copyright (c) 2021 Kian Meng, Ang <kianmeng.ang@gmail.com>
# Copyright (c) 2021 Dmitry Shachnev <mitya57@users.noreply.github.com>
# Copyright (c) 2021 David Liu <david@cs.toronto.edu>
# Copyright (c) 2021 pre-commit-ci[bot] <bot@noreply.github.com>
# Copyright (c) 2021 doranid <ddandd@gmail.com>
# Copyright (c) 2021 Andrew Haigh <hello@nelf.in>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE


"""
This module contains the classes for "scoped" node, i.e. which are opening a
new local scope in the language definition : Module, ClassDef, FunctionDef (and
Lambda, GeneratorExp, DictComp and SetComp to some extent).
"""
import builtins
import io
import itertools
import os
import sys
import typing
import warnings
from typing import Dict, List, Optional, Set, TypeVar, Union, overload

from astroid import bases
from astroid import decorators as decorators_mod
from astroid import mixins, util
from astroid.const import PY38_PLUS, PY39_PLUS
from astroid.context import (
    CallContext,
    InferenceContext,
    bind_context_to_node,
    copy_context,
)
from astroid.exceptions import (
    AstroidBuildingError,
    AstroidTypeError,
    AttributeInferenceError,
    DuplicateBasesError,
    InconsistentMroError,
    InferenceError,
    MroError,
    StatementMissing,
    TooManyLevelsError,
)
from astroid.filter_statements import _filter_stmts
from astroid.interpreter.dunder_lookup import lookup
from astroid.interpreter.objectmodel import ClassModel, FunctionModel, ModuleModel
from astroid.manager import AstroidManager
from astroid.nodes import Arguments, Const, node_classes

if sys.version_info >= (3, 6, 2):
    from typing import NoReturn
else:
    from typing_extensions import NoReturn


if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


ITER_METHODS = ("__iter__", "__getitem__")
EXCEPTION_BASE_CLASSES = frozenset({"Exception", "BaseException"})
objects = util.lazy_import("objects")
BUILTIN_DESCRIPTORS = frozenset(
    {"classmethod", "staticmethod", "builtins.classmethod", "builtins.staticmethod"}
)

T = TypeVar("T")


def _c3_merge(sequences, cls, context):
    """Merges MROs in *sequences* to a single MRO using the C3 algorithm.

    Adapted from http://www.python.org/download/releases/2.3/mro/.

    """
    result = []
    while True:
        sequences = [s for s in sequences if s]  # purge empty sequences
        if not sequences:
            return result
        for s1 in sequences:  # find merge candidates among seq heads
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break  # reject the current head, it appears later
            else:
                break
        if not candidate:
            # Show all the remaining bases, which were considered as
            # candidates for the next mro sequence.
            raise InconsistentMroError(
                message="Cannot create a consistent method resolution order "
                "for MROs {mros} of class {cls!r}.",
                mros=sequences,
                cls=cls,
                context=context,
            )

        result.append(candidate)
        # remove the chosen candidate
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]
    return None


def clean_typing_generic_mro(sequences: List[List["ClassDef"]]) -> None:
    """A class can inherit from typing.Generic directly, as base,
    and as base of bases. The merged MRO must however only contain the last entry.
    To prepare for _c3_merge, remove some typing.Generic entries from
    sequences if multiple are present.

    This method will check if Generic is in inferred_bases and also
    part of bases_mro. If true, remove it from inferred_bases
    as well as its entry the bases_mro.

    Format sequences: [[self]] + bases_mro + [inferred_bases]
    """
    bases_mro = sequences[1:-1]
    inferred_bases = sequences[-1]
    # Check if Generic is part of inferred_bases
    for i, base in enumerate(inferred_bases):
        if base.qname() == "typing.Generic":
            position_in_inferred_bases = i
            break
    else:
        return
    # Check if also part of bases_mro
    # Ignore entry for typing.Generic
    for i, seq in enumerate(bases_mro):
        if i == position_in_inferred_bases:
            continue
        if any(base.qname() == "typing.Generic" for base in seq):
            break
    else:
        return
    # Found multiple Generics in mro, remove entry from inferred_bases
    # and the corresponding one from bases_mro
    inferred_bases.pop(position_in_inferred_bases)
    bases_mro.pop(position_in_inferred_bases)


def clean_duplicates_mro(sequences, cls, context):
    for sequence in sequences:
        names = [
            (node.lineno, node.qname()) if node.name else None for node in sequence
        ]
        last_index = dict(map(reversed, enumerate(names)))
        if names and names[0] is not None and last_index[names[0]] != 0:
            raise DuplicateBasesError(
                message="Duplicates found in MROs {mros} for {cls!r}.",
                mros=sequences,
                cls=cls,
                context=context,
            )
        yield [
            node
            for i, (node, name) in enumerate(zip(sequence, names))
            if name is None or last_index[name] == i
        ]


def function_to_method(n, klass):
    if isinstance(n, FunctionDef):
        if n.type == "classmethod":
            return bases.BoundMethod(n, klass)
        if n.type == "property":
            return n
        if n.type != "staticmethod":
            return bases.UnboundMethod(n)
    return n


def builtin_lookup(name):
    """lookup a name into the builtin module
    return the list of matching statements and the astroid for the builtin
    module
    """
    builtin_astroid = AstroidManager().ast_from_module(builtins)
    if name == "__dict__":
        return builtin_astroid, ()
    try:
        stmts = builtin_astroid.locals[name]
    except KeyError:
        stmts = ()
    return builtin_astroid, stmts


# TODO move this Mixin to mixins.py; problem: 'FunctionDef' in _scope_lookup
class LocalsDictNodeNG(node_classes.LookupMixIn, node_classes.NodeNG):
    """this class provides locals handling common to Module, FunctionDef
    and ClassDef nodes, including a dict like interface for direct access
    to locals information
    """

    # attributes below are set by the builder module or by raw factories

    locals: Dict[str, List[node_classes.NodeNG]] = {}
    """A map of the name of a local variable to the node defining the local."""

    def qname(self):
        """Get the 'qualified' name of the node.

        For example: module.name, module.class.name ...

        :returns: The qualified name.
        :rtype: str
        """
        # pylint: disable=no-member; github.com/pycqa/astroid/issues/278
        if self.parent is None:
            return self.name
        return f"{self.parent.frame(future=True).qname()}.{self.name}"

    def scope(self: T) -> T:
        """The first parent node defining a new scope.

        :returns: The first parent scope node.
        :rtype: Module or FunctionDef or ClassDef or Lambda or GenExpr
        """
        return self

    def _scope_lookup(self, node, name, offset=0):
        """XXX method for interfacing the scope lookup"""
        try:
            stmts = _filter_stmts(node, self.locals[name], self, offset)
        except KeyError:
            stmts = ()
        if stmts:
            return self, stmts

        # Handle nested scopes: since class names do not extend to nested
        # scopes (e.g., methods), we find the next enclosing non-class scope
        pscope = self.parent and self.parent.scope()
        while pscope is not None:
            if not isinstance(pscope, ClassDef):
                return pscope.scope_lookup(node, name)
            pscope = pscope.parent and pscope.parent.scope()

        # self is at the top level of a module, or is enclosed only by ClassDefs
        return builtin_lookup(name)

    def set_local(self, name, stmt):
        """Define that the given name is declared in the given statement node.

        .. seealso:: :meth:`scope`

        :param name: The name that is being defined.
        :type name: str

        :param stmt: The statement that defines the given name.
        :type stmt: NodeNG
        """
        # assert not stmt in self.locals.get(name, ()), (self, stmt)
        self.locals.setdefault(name, []).append(stmt)

    __setitem__ = set_local

    def _append_node(self, child):
        """append a child, linking it in the tree"""
        # pylint: disable=no-member; depending by the class
        # which uses the current class as a mixin or base class.
        # It's rewritten in 2.0, so it makes no sense for now
        # to spend development time on it.
        self.body.append(child)
        child.parent = self

    def add_local_node(self, child_node, name=None):
        """Append a child that should alter the locals of this scope node.

        :param child_node: The child node that will alter locals.
        :type child_node: NodeNG

        :param name: The name of the local that will be altered by
            the given child node.
        :type name: str or None
        """
        if name != "__class__":
            # add __class__ node as a child will cause infinite recursion later!
            self._append_node(child_node)
        self.set_local(name or child_node.name, child_node)

    def __getitem__(self, item):
        """The first node the defines the given local.

        :param item: The name of the locally defined object.
        :type item: str

        :raises KeyError: If the name is not defined.
        """
        return self.locals[item][0]

    def __iter__(self):
        """Iterate over the names of locals defined in this scoped node.

        :returns: The names of the defined locals.
        :rtype: iterable(str)
        """
        return iter(self.keys())

    def keys(self):
        """The names of locals defined in this scoped node.

        :returns: The names of the defined locals.
        :rtype: list(str)
        """
        return list(self.locals.keys())

    def values(self):
        """The nodes that define the locals in this scoped node.

        :returns: The nodes that define locals.
        :rtype: list(NodeNG)
        """
        # pylint: disable=consider-using-dict-items
        # It look like this class override items/keys/values,
        # probably not worth the headache
        return [self[key] for key in self.keys()]

    def items(self):
        """Get the names of the locals and the node that defines the local.

        :returns: The names of locals and their associated node.
        :rtype: list(tuple(str, NodeNG))
        """
        return list(zip(self.keys(), self.values()))

    def __contains__(self, name):
        """Check if a local is defined in this scope.

        :param name: The name of the local to check for.
        :type name: str

        :returns: True if this node has a local of the given name,
            False otherwise.
        :rtype: bool
        """
        return name in self.locals


class Module(LocalsDictNodeNG):
    """Class representing an :class:`ast.Module` node.

    >>> import astroid
    >>> node = astroid.extract_node('import astroid')
    >>> node
    <Import l.1 at 0x7f23b2e4e5c0>
    >>> node.parent
    <Module l.0 at 0x7f23b2e4eda0>
    """

    _astroid_fields = ("body",)

    fromlineno: Literal[0] = 0
    """The first line that this node appears on in the source code."""

    lineno: Literal[0] = 0
    """The line that this node appears on in the source code."""

    # attributes below are set by the builder module or by raw factories

    file_bytes: Union[str, bytes, None] = None
    """The string/bytes that this ast was built from."""

    file_encoding: Optional[str] = None
    """The encoding of the source file.

    This is used to get unicode out of a source file.
    Python 2 only.
    """

    special_attributes = ModuleModel()
    """The names of special attributes that this module has."""

    # names of module attributes available through the global scope
    scope_attrs = {"__name__", "__doc__", "__file__", "__path__", "__package__"}
    """The names of module attributes available through the global scope."""

    _other_fields = (
        "name",
        "doc",
        "file",
        "path",
        "package",
        "pure_python",
        "future_imports",
    )
    _other_other_fields = ("locals", "globals")

    col_offset: None
    end_lineno: None
    end_col_offset: None
    parent: None

    def __init__(
        self,
        name: str,
        doc: Optional[str],
        file: Optional[str] = None,
        path: Optional[List[str]] = None,
        package: Optional[bool] = None,
        parent: Literal[None] = None,
        pure_python: Optional[bool] = True,
    ) -> None:
        """
        :param name: The name of the module.

        :param doc: The module docstring.

        :param file: The path to the file that this ast has been extracted from.

        :param path:

        :param package: Whether the node represents a package or a module.

        :param parent: The parent node in the syntax tree.

        :param pure_python: Whether the ast was built from source.
        """
        self.name = name
        """The name of the module."""

        self.doc = doc
        """The module docstring."""

        self.file = file
        """The path to the file that this ast has been extracted from.

        This will be ``None`` when the representation has been built from a
        built-in module.
        """

        self.path = path

        self.package = package
        """Whether the node represents a package or a module."""

        self.pure_python = pure_python
        """Whether the ast was built from source."""

        self.globals: Dict[str, List[node_classes.NodeNG]]
        """A map of the name of a global variable to the node defining the global."""

        self.locals = self.globals = {}

        self.body: Optional[List[node_classes.NodeNG]] = []
        """The contents of the module."""

        self.future_imports: Set[str] = set()
        """The imports from ``__future__``."""

        super().__init__(lineno=0, parent=parent)

    # pylint: enable=redefined-builtin

    def postinit(self, body=None):
        """Do some setup after initialisation.

        :param body: The contents of the module.
        :type body: list(NodeNG) or None
        """
        self.body = body

    def _get_stream(self):
        if self.file_bytes is not None:
            return io.BytesIO(self.file_bytes)
        if self.file is not None:
            # pylint: disable=consider-using-with
            stream = open(self.file, "rb")
            return stream
        return None

    def stream(self):
        """Get a stream to the underlying file or bytes.

        :type: file or io.BytesIO or None
        """
        return self._get_stream()

    def block_range(self, lineno):
        """Get a range from where this node starts to where this node ends.

        :param lineno: Unused.
        :type lineno: int

        :returns: The range of line numbers that this node belongs to.
        :rtype: tuple(int, int)
        """
        return self.fromlineno, self.tolineno

    def scope_lookup(self, node, name, offset=0):
        """Lookup where the given variable is assigned.

        :param node: The node to look for assignments up to.
            Any assignments after the given node are ignored.
        :type node: NodeNG

        :param name: The name of the variable to find assignments for.
        :type name: str

        :param offset: The line offset to filter statements up to.
        :type offset: int

        :returns: This scope node and the list of assignments associated to the
            given name according to the scope where it has been found (locals,
            globals or builtin).
        :rtype: tuple(str, list(NodeNG))
        """
        if name in self.scope_attrs and name not in self.locals:
            try:
                return self, self.getattr(name)
            except AttributeInferenceError:
                return self, ()
        return self._scope_lookup(node, name, offset)

    def pytype(self):
        """Get the name of the type that this node represents.

        :returns: The name of the type.
        :rtype: str
        """
        return "builtins.module"

    def display_type(self):
        """A human readable type of this node.

        :returns: The type of this node.
        :rtype: str
        """
        return "Module"

    def getattr(self, name, context=None, ignore_locals=False):
        if not name:
            raise AttributeInferenceError(target=self, attribute=name, context=context)

        result = []
        name_in_locals = name in self.locals

        if name in self.special_attributes and not ignore_locals and not name_in_locals:
            result = [self.special_attributes.lookup(name)]
        elif not ignore_locals and name_in_locals:
            result = self.locals[name]
        elif self.package:
            try:
                result = [self.import_module(name, relative_only=True)]
            except (AstroidBuildingError, SyntaxError) as exc:
                raise AttributeInferenceError(
                    target=self, attribute=name, context=context
                ) from exc
        result = [n for n in result if not isinstance(n, node_classes.DelName)]
        if result:
            return result
        raise AttributeInferenceError(target=self, attribute=name, context=context)

    def igetattr(self, name, context=None):
        """Infer the possible values of the given variable.

        :param name: The name of the variable to infer.
        :type name: str

        :returns: The inferred possible values.
        :rtype: iterable(NodeNG) or None
        """
        # set lookup name since this is necessary to infer on import nodes for
        # instance
        context = copy_context(context)
        context.lookupname = name
        try:
            return bases._infer_stmts(self.getattr(name, context), context, frame=self)
        except AttributeInferenceError as error:
            raise InferenceError(
                str(error), target=self, attribute=name, context=context
            ) from error

    def fully_defined(self):
        """Check if this module has been build from a .py file.

        If so, the module contains a complete representation,
        including the code.

        :returns: True if the module has been built from a .py file.
        :rtype: bool
        """
        return self.file is not None and self.file.endswith(".py")

    @overload
    def statement(self, *, future: Literal[None] = ...) -> "Module":
        ...

    # pylint: disable-next=arguments-differ
    # https://github.com/PyCQA/pylint/issues/5264
    @overload
    def statement(self, *, future: Literal[True]) -> NoReturn:
        ...

    def statement(
        self, *, future: Literal[None, True] = None
    ) -> Union["NoReturn", "Module"]:
        """The first parent node, including self, marked as statement node.

        When called on a :class:`Module` with the future parameter this raises an error.

        TODO: Deprecate the future parameter and only raise StatementMissing

        :raises StatementMissing: If no self has no parent attribute and future is True
        """
        if future:
            raise StatementMissing(target=self)
        warnings.warn(
            "In astroid 3.0.0 NodeNG.statement() will return either a nodes.Statement "
            "or raise a StatementMissing exception. nodes.Module will no longer be "
            "considered a statement. This behaviour can already be triggered "
            "by passing 'future=True' to a statement() call.",
            DeprecationWarning,
        )
        return self

    def previous_sibling(self):
        """The previous sibling statement.

        :returns: The previous sibling statement node.
        :rtype: NodeNG or None
        """

    def next_sibling(self):
        """The next sibling statement node.

        :returns: The next sibling statement node.
        :rtype: NodeNG or None
        """

    _absolute_import_activated = True

    def absolute_import_activated(self):
        """Whether :pep:`328` absolute import behaviour has been enabled.

        :returns: True if :pep:`328` has been enabled, False otherwise.
        :rtype: bool
        """
        return self._absolute_import_activated

    def import_module(self, modname, relative_only=False, level=None):
        """Get the ast for a given module as if imported from this module.

        :param modname: The name of the module to "import".
        :type modname: str

        :param relative_only: Whether to only consider relative imports.
        :type relative_only: bool

        :param level: The level of relative import.
        :type level: int or None

        :returns: The imported module ast.
        :rtype: NodeNG
        """
        if relative_only and level is None:
            level = 0
        absmodname = self.relative_to_absolute_name(modname, level)

        try:
            return AstroidManager().ast_from_module_name(absmodname)
        except AstroidBuildingError:
            # we only want to import a sub module or package of this module,
            # skip here
            if relative_only:
                raise
        return AstroidManager().ast_from_module_name(modname)

    def relative_to_absolute_name(self, modname: str, level: int) -> str:
        """Get the absolute module name for a relative import.

        The relative import can be implicit or explicit.

        :param modname: The module name to convert.

        :param level: The level of relative import.

        :returns: The absolute module name.

        :raises TooManyLevelsError: When the relative import refers to a
            module too far above this one.
        """
        # XXX this returns non sens when called on an absolute import
        # like 'pylint.checkers.astroid.utils'
        # XXX doesn't return absolute name if self.name isn't absolute name
        if self.absolute_import_activated() and level is None:
            return modname
        if level:
            if self.package:
                level = level - 1
                package_name = self.name.rsplit(".", level)[0]
            elif (
                self.path
                and not os.path.exists(os.path.dirname(self.path[0]) + "/__init__.py")
                and os.path.exists(
                    os.path.dirname(self.path[0]) + "/" + modname.split(".")[0]
                )
            ):
                level = level - 1
                package_name = ""
            else:
                package_name = self.name.rsplit(".", level)[0]
            if level and self.name.count(".") < level:
                raise TooManyLevelsError(level=level, name=self.name)

        elif self.package:
            package_name = self.name
        else:
            package_name = self.name.rsplit(".", 1)[0]

        if package_name:
            if not modname:
                return package_name
            return f"{package_name}.{modname}"
        return modname

    def wildcard_import_names(self):
        """The list of imported names when this module is 'wildcard imported'.

        It doesn't include the '__builtins__' name which is added by the
        current CPython implementation of wildcard imports.

        :returns: The list of imported names.
        :rtype: list(str)
        """
        # We separate the different steps of lookup in try/excepts
        # to avoid catching too many Exceptions
        default = [name for name in self.keys() if not name.startswith("_")]
        try:
            all_values = self["__all__"]
        except KeyError:
            return default

        try:
            explicit = next(all_values.assigned_stmts())
        except (InferenceError, StopIteration):
            return default
        except AttributeError:
            # not an assignment node
            # XXX infer?
            return default

        # Try our best to detect the exported name.
        inferred = []
        try:
            explicit = next(explicit.infer())
        except (InferenceError, StopIteration):
            return default
        if not isinstance(explicit, (node_classes.Tuple, node_classes.List)):
            return default

        def str_const(node):
            return isinstance(node, node_classes.Const) and isinstance(node.value, str)

        for node in explicit.elts:
            if str_const(node):
                inferred.append(node.value)
            else:
                try:
                    inferred_node = next(node.infer())
                except (InferenceError, StopIteration):
                    continue
                if str_const(inferred_node):
                    inferred.append(inferred_node.value)
        return inferred

    def public_names(self):
        """The list of the names that are publicly available in this module.

        :returns: The list of public names.
        :rtype: list(str)
        """
        return [name for name in self.keys() if not name.startswith("_")]

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`Module` this is always ``True``.
        :rtype: bool
        """
        return True

    def get_children(self):
        yield from self.body

    def frame(self: T, *, future: Literal[None, True] = None) -> T:
        """The node's frame node.

        A frame node is a :class:`Module`, :class:`FunctionDef`,
        :class:`ClassDef` or :class:`Lambda`.

        :returns: The node itself.
        """
        return self


class ComprehensionScope(LocalsDictNodeNG):
    """Scoping for different types of comprehensions."""

    scope_lookup = LocalsDictNodeNG._scope_lookup


class GeneratorExp(ComprehensionScope):
    """Class representing an :class:`ast.GeneratorExp` node.

    >>> import astroid
    >>> node = astroid.extract_node('(thing for thing in things if thing)')
    >>> node
    <GeneratorExp l.1 at 0x7f23b2e4e400>
    """

    _astroid_fields = ("elt", "generators")
    _other_other_fields = ("locals",)
    elt = None
    """The element that forms the output of the expression.

    :type: NodeNG or None
    """
    generators = None
    """The generators that are looped through.

    :type: list(Comprehension) or None
    """

    def __init__(
        self,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        """
        :param lineno: The line that this node appears on in the source code.
        :type lineno: int or None

        :param col_offset: The column that this node appears on in the
            source code.
        :type col_offset: int or None

        :param parent: The parent node in the syntax tree.
        :type parent: NodeNG or None

        :param end_lineno: The last line this node appears on in the source code.
        :type end_lineno: Optional[int]

        :param end_col_offset: The end column this node appears on in the
            source code. Note: This is after the last symbol.
        :type end_col_offset: Optional[int]
        """
        self.locals = {}
        """A map of the name of a local variable to the node defining the local.

        :type: dict(str, NodeNG)
        """

        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )

    def postinit(self, elt=None, generators=None):
        """Do some setup after initialisation.

        :param elt: The element that forms the output of the expression.
        :type elt: NodeNG or None

        :param generators: The generators that are looped through.
        :type generators: list(Comprehension) or None
        """
        self.elt = elt
        if generators is None:
            self.generators = []
        else:
            self.generators = generators

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`GeneratorExp` this is always ``True``.
        :rtype: bool
        """
        return True

    def get_children(self):
        yield self.elt

        yield from self.generators


class DictComp(ComprehensionScope):
    """Class representing an :class:`ast.DictComp` node.

    >>> import astroid
    >>> node = astroid.extract_node('{k:v for k, v in things if k > v}')
    >>> node
    <DictComp l.1 at 0x7f23b2e41d68>
    """

    _astroid_fields = ("key", "value", "generators")
    _other_other_fields = ("locals",)
    key = None
    """What produces the keys.

    :type: NodeNG or None
    """
    value = None
    """What produces the values.

    :type: NodeNG or None
    """
    generators = None
    """The generators that are looped through.

    :type: list(Comprehension) or None
    """

    def __init__(
        self,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        """
        :param lineno: The line that this node appears on in the source code.
        :type lineno: int or None

        :param col_offset: The column that this node appears on in the
            source code.
        :type col_offset: int or None

        :param parent: The parent node in the syntax tree.
        :type parent: NodeNG or None

        :param end_lineno: The last line this node appears on in the source code.
        :type end_lineno: Optional[int]

        :param end_col_offset: The end column this node appears on in the
            source code. Note: This is after the last symbol.
        :type end_col_offset: Optional[int]
        """
        self.locals = {}
        """A map of the name of a local variable to the node defining the local.

        :type: dict(str, NodeNG)
        """

        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )

    def postinit(self, key=None, value=None, generators=None):
        """Do some setup after initialisation.

        :param key: What produces the keys.
        :type key: NodeNG or None

        :param value: What produces the values.
        :type value: NodeNG or None

        :param generators: The generators that are looped through.
        :type generators: list(Comprehension) or None
        """
        self.key = key
        self.value = value
        if generators is None:
            self.generators = []
        else:
            self.generators = generators

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`DictComp` this is always :class:`Uninferable`.
        :rtype: Uninferable
        """
        return util.Uninferable

    def get_children(self):
        yield self.key
        yield self.value

        yield from self.generators


class SetComp(ComprehensionScope):
    """Class representing an :class:`ast.SetComp` node.

    >>> import astroid
    >>> node = astroid.extract_node('{thing for thing in things if thing}')
    >>> node
    <SetComp l.1 at 0x7f23b2e41898>
    """

    _astroid_fields = ("elt", "generators")
    _other_other_fields = ("locals",)
    elt = None
    """The element that forms the output of the expression.

    :type: NodeNG or None
    """
    generators = None
    """The generators that are looped through.

    :type: list(Comprehension) or None
    """

    def __init__(
        self,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        """
        :param lineno: The line that this node appears on in the source code.
        :type lineno: int or None

        :param col_offset: The column that this node appears on in the
            source code.
        :type col_offset: int or None

        :param parent: The parent node in the syntax tree.
        :type parent: NodeNG or None

        :param end_lineno: The last line this node appears on in the source code.
        :type end_lineno: Optional[int]

        :param end_col_offset: The end column this node appears on in the
            source code. Note: This is after the last symbol.
        :type end_col_offset: Optional[int]
        """
        self.locals = {}
        """A map of the name of a local variable to the node defining the local.

        :type: dict(str, NodeNG)
        """

        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )

    def postinit(self, elt=None, generators=None):
        """Do some setup after initialisation.

        :param elt: The element that forms the output of the expression.
        :type elt: NodeNG or None

        :param generators: The generators that are looped through.
        :type generators: list(Comprehension) or None
        """
        self.elt = elt
        if generators is None:
            self.generators = []
        else:
            self.generators = generators

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`SetComp` this is always :class:`Uninferable`.
        :rtype: Uninferable
        """
        return util.Uninferable

    def get_children(self):
        yield self.elt

        yield from self.generators


class _ListComp(node_classes.NodeNG):
    """Class representing an :class:`ast.ListComp` node.

    >>> import astroid
    >>> node = astroid.extract_node('[thing for thing in things if thing]')
    >>> node
    <ListComp l.1 at 0x7f23b2e418d0>
    """

    _astroid_fields = ("elt", "generators")
    elt = None
    """The element that forms the output of the expression.

    :type: NodeNG or None
    """
    generators = None
    """The generators that are looped through.

    :type: list(Comprehension) or None
    """

    def postinit(self, elt=None, generators=None):
        """Do some setup after initialisation.

        :param elt: The element that forms the output of the expression.
        :type elt: NodeNG or None

        :param generators: The generators that are looped through.
        :type generators: list(Comprehension) or None
        """
        self.elt = elt
        self.generators = generators

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`ListComp` this is always :class:`Uninferable`.
        :rtype: Uninferable
        """
        return util.Uninferable

    def get_children(self):
        yield self.elt

        yield from self.generators


class ListComp(_ListComp, ComprehensionScope):
    """Class representing an :class:`ast.ListComp` node.

    >>> import astroid
    >>> node = astroid.extract_node('[thing for thing in things if thing]')
    >>> node
    <ListComp l.1 at 0x7f23b2e418d0>
    """

    _other_other_fields = ("locals",)

    def __init__(
        self,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        self.locals = {}
        """A map of the name of a local variable to the node defining it.

        :type: dict(str, NodeNG)
        """

        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )


def _infer_decorator_callchain(node):
    """Detect decorator call chaining and see if the end result is a
    static or a classmethod.
    """
    if not isinstance(node, FunctionDef):
        return None
    if not node.parent:
        return None
    try:
        result = next(node.infer_call_result(node.parent), None)
    except InferenceError:
        return None
    if isinstance(result, bases.Instance):
        result = result._proxied
    if isinstance(result, ClassDef):
        if result.is_subtype_of("builtins.classmethod"):
            return "classmethod"
        if result.is_subtype_of("builtins.staticmethod"):
            return "staticmethod"
    if isinstance(result, FunctionDef):
        if not result.decorators:
            return None
        # Determine if this function is decorated with one of the builtin descriptors we want.
        for decorator in result.decorators.nodes:
            if isinstance(decorator, node_classes.Name):
                if decorator.name in BUILTIN_DESCRIPTORS:
                    return decorator.name
            if (
                isinstance(decorator, node_classes.Attribute)
                and isinstance(decorator.expr, node_classes.Name)
                and decorator.expr.name == "builtins"
                and decorator.attrname in BUILTIN_DESCRIPTORS
            ):
                return decorator.attrname
    return None


class Lambda(mixins.FilterStmtsMixin, LocalsDictNodeNG):
    """Class representing an :class:`ast.Lambda` node.

    >>> import astroid
    >>> node = astroid.extract_node('lambda arg: arg + 1')
    >>> node
    <Lambda.<lambda> l.1 at 0x7f23b2e41518>
    """

    _astroid_fields = ("args", "body")
    _other_other_fields = ("locals",)
    name = "<lambda>"
    is_lambda = True

    def implicit_parameters(self):
        return 0

    # function's type, 'function' | 'method' | 'staticmethod' | 'classmethod'
    @property
    def type(self):
        """Whether this is a method or function.

        :returns: 'method' if this is a method, 'function' otherwise.
        :rtype: str
        """
        if self.args.arguments and self.args.arguments[0].name == "self":
            if isinstance(self.parent.scope(), ClassDef):
                return "method"
        return "function"

    def __init__(
        self,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        """
        :param lineno: The line that this node appears on in the source code.
        :type lineno: int or None

        :param col_offset: The column that this node appears on in the
            source code.
        :type col_offset: int or None

        :param parent: The parent node in the syntax tree.
        :type parent: NodeNG or None

        :param end_lineno: The last line this node appears on in the source code.
        :type end_lineno: Optional[int]

        :param end_col_offset: The end column this node appears on in the
            source code. Note: This is after the last symbol.
        :type end_col_offset: Optional[int]
        """
        self.locals = {}
        """A map of the name of a local variable to the node defining it.

        :type: dict(str, NodeNG)
        """

        self.args: Arguments
        """The arguments that the function takes."""

        self.body = []
        """The contents of the function body.

        :type: list(NodeNG)
        """

        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )

    def postinit(self, args: Arguments, body):
        """Do some setup after initialisation.

        :param args: The arguments that the function takes.

        :param body: The contents of the function body.
        :type body: list(NodeNG)
        """
        self.args = args
        self.body = body

    def pytype(self):
        """Get the name of the type that this node represents.

        :returns: The name of the type.
        :rtype: str
        """
        if "method" in self.type:
            return "builtins.instancemethod"
        return "builtins.function"

    def display_type(self):
        """A human readable type of this node.

        :returns: The type of this node.
        :rtype: str
        """
        if "method" in self.type:
            return "Method"
        return "Function"

    def callable(self):
        """Whether this node defines something that is callable.

        :returns: True if this defines something that is callable,
            False otherwise.
            For a :class:`Lambda` this is always ``True``.
        :rtype: bool
        """
        return True

    def argnames(self) -> List[str]:
        """Get the names of each of the arguments, including that
        of the collections of variable-length arguments ("args", "kwargs",
        etc.), as well as positional-only and keyword-only arguments.

        :returns: The names of the arguments.
        :rtype: list(str)
        """
        if self.args.arguments:  # maybe None with builtin functions
            names = _rec_get_names(self.args.arguments)
        else:
            names = []
        if self.args.vararg:
            names.append(self.args.vararg)
        names += [elt.name for elt in self.args.kwonlyargs]
        if self.args.kwarg:
            names.append(self.args.kwarg)
        return names

    def infer_call_result(self, caller, context=None):
        """Infer what the function returns when called.

        :param caller: Unused
        :type caller: object
        """
        # pylint: disable=no-member; github.com/pycqa/astroid/issues/291
        # args is in fact redefined later on by postinit. Can't be changed
        # to None due to a strong interaction between Lambda and FunctionDef.
        return self.body.infer(context)

    def scope_lookup(self, node, name, offset=0):
        """Lookup where the given names is assigned.

        :param node: The node to look for assignments up to.
            Any assignments after the given node are ignored.
        :type node: NodeNG

        :param name: The name to find assignments for.
        :type name: str

        :param offset: The line offset to filter statements up to.
        :type offset: int

        :returns: This scope node and the list of assignments associated to the
            given name according to the scope where it has been found (locals,
            globals or builtin).
        :rtype: tuple(str, list(NodeNG))
        """
        if node in self.args.defaults or node in self.args.kw_defaults:
            frame = self.parent.frame(future=True)
            # line offset to avoid that def func(f=func) resolve the default
            # value to the defined function
            offset = -1
        else:
            # check this is not used in function decorators
            frame = self
        return frame._scope_lookup(node, name, offset)

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`Lambda` this is always ``True``.
        :rtype: bool
        """
        return True

    def get_children(self):
        yield self.args
        yield self.body

    def frame(self: T, *, future: Literal[None, True] = None) -> T:
        """The node's frame node.

        A frame node is a :class:`Module`, :class:`FunctionDef`,
        :class:`ClassDef` or :class:`Lambda`.

        :returns: The node itself.
        """
        return self


class FunctionDef(mixins.MultiLineBlockMixin, node_classes.Statement, Lambda):
    """Class representing an :class:`ast.FunctionDef`.

    >>> import astroid
    >>> node = astroid.extract_node('''
    ... def my_func(arg):
    ...     return arg + 1
    ... ''')
    >>> node
    <FunctionDef.my_func l.2 at 0x7f23b2e71e10>
    """

    _astroid_fields = ("decorators", "args", "returns", "body")
    _multi_line_block_fields = ("body",)
    returns = None
    decorators: Optional[node_classes.Decorators] = None
    """The decorators that are applied to this method or function."""
    special_attributes = FunctionModel()
    """The names of special attributes that this function has.

    :type: objectmodel.FunctionModel
    """
    is_function = True
    """Whether this node indicates a function.

    For a :class:`FunctionDef` this is always ``True``.

    :type: bool
    """
    type_annotation = None
    """If present, this will contain the type annotation passed by a type comment

    :type: NodeNG or None
    """
    type_comment_args = None
    """
    If present, this will contain the type annotation for arguments
    passed by a type comment
    """
    type_comment_returns = None
    """If present, this will contain the return type annotation, passed by a type comment"""
    # attributes below are set by the builder module or by raw factories
    _other_fields = ("name", "doc")
    _other_other_fields = (
        "locals",
        "_type",
        "type_comment_returns",
        "type_comment_args",
    )
    _type = None

    def __init__(
        self,
        name=None,
        doc=None,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        """
        :param name: The name of the function.
        :type name: str or None

        :param doc: The function's docstring.
        :type doc: str or None

        :param lineno: The line that this node appears on in the source code.
        :type lineno: int or None

        :param col_offset: The column that this node appears on in the
            source code.
        :type col_offset: int or None

        :param parent: The parent node in the syntax tree.
        :type parent: NodeNG or None

        :param end_lineno: The last line this node appears on in the source code.
        :type end_lineno: Optional[int]

        :param end_col_offset: The end column this node appears on in the
            source code. Note: This is after the last symbol.
        :type end_col_offset: Optional[int]
        """
        self.name = name
        """The name of the function.

        :type name: str or None
        """

        self.doc = doc
        """The function's docstring.

        :type doc: str or None
        """

        self.instance_attrs = {}
        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )
        if parent:
            frame = parent.frame(future=True)
            frame.set_local(name, self)

    # pylint: disable=arguments-differ; different than Lambdas
    def postinit(
        self,
        args: Arguments,
        body,
        decorators: Optional[node_classes.Decorators] = None,
        returns=None,
        type_comment_returns=None,
        type_comment_args=None,
    ):
        """Do some setup after initialisation.

        :param args: The arguments that the function takes.

        :param body: The contents of the function body.
        :type body: list(NodeNG)

        :param decorators: The decorators that are applied to this
            method or function.
        :type decorators: Decorators or None
        :params type_comment_returns:
            The return type annotation passed via a type comment.
        :params type_comment_args:
            The args type annotation passed via a type comment.
        """
        self.args = args
        self.body = body
        self.decorators = decorators
        self.returns = returns
        self.type_comment_returns = type_comment_returns
        self.type_comment_args = type_comment_args

    @decorators_mod.cachedproperty
    def extra_decorators(self) -> List[node_classes.Call]:
        """The extra decorators that this function can have.

        Additional decorators are considered when they are used as
        assignments, as in ``method = staticmethod(method)``.
        The property will return all the callables that are used for
        decoration.
        """
        frame = self.parent.frame(future=True)
        if not isinstance(frame, ClassDef):
            return []

        decorators: List[node_classes.Call] = []
        for assign in frame._get_assign_nodes():
            if isinstance(assign.value, node_classes.Call) and isinstance(
                assign.value.func, node_classes.Name
            ):
                for assign_node in assign.targets:
                    if not isinstance(assign_node, node_classes.AssignName):
                        # Support only `name = callable(name)`
                        continue

                    if assign_node.name != self.name:
                        # Interested only in the assignment nodes that
                        # decorates the current method.
                        continue
                    try:
                        meth = frame[self.name]
                    except KeyError:
                        continue
                    else:
                        # Must be a function and in the same frame as the
                        # original method.
                        if (
                            isinstance(meth, FunctionDef)
                            and assign_node.frame(future=True) == frame
                        ):
                            decorators.append(assign.value)
        return decorators

    @decorators_mod.cachedproperty
    def type(
        self,
    ):  # pylint: disable=invalid-overridden-method,too-many-return-statements
        """The function type for this node.

        Possible values are: method, function, staticmethod, classmethod.

        :type: str
        """
        for decorator in self.extra_decorators:
            if decorator.func.name in BUILTIN_DESCRIPTORS:
                return decorator.func.name

        frame = self.parent.frame(future=True)
        type_name = "function"
        if isinstance(frame, ClassDef):
            if self.name == "__new__":
                return "classmethod"
            if self.name == "__init_subclass__":
                return "classmethod"
            if self.name == "__class_getitem__":
                return "classmethod"

            type_name = "method"

        if not self.decorators:
            return type_name

        for node in self.decorators.nodes:
            if isinstance(node, node_classes.Name):
                if node.name in BUILTIN_DESCRIPTORS:
                    return node.name
            if (
                isinstance(node, node_classes.Attribute)
                and isinstance(node.expr, node_classes.Name)
                and node.expr.name == "builtins"
                and node.attrname in BUILTIN_DESCRIPTORS
            ):
                return node.attrname

            if isinstance(node, node_classes.Call):
                # Handle the following case:
                # @some_decorator(arg1, arg2)
                # def func(...)
                #
                try:
                    current = next(node.func.infer())
                except (InferenceError, StopIteration):
                    continue
                _type = _infer_decorator_callchain(current)
                if _type is not None:
                    return _type

            try:
                for inferred in node.infer():
                    # Check to see if this returns a static or a class method.
                    _type = _infer_decorator_callchain(inferred)
                    if _type is not None:
                        return _type

                    if not isinstance(inferred, ClassDef):
                        continue
                    for ancestor in inferred.ancestors():
                        if not isinstance(ancestor, ClassDef):
                            continue
                        if ancestor.is_subtype_of("builtins.classmethod"):
                            return "classmethod"
                        if ancestor.is_subtype_of("builtins.staticmethod"):
                            return "staticmethod"
            except InferenceError:
                pass
        return type_name

    @decorators_mod.cachedproperty
    def fromlineno(self) -> Optional[int]:
        """The first line that this node appears on in the source code."""
        # lineno is the line number of the first decorator, we want the def
        # statement lineno. Similar to 'ClassDef.fromlineno'
        lineno = self.lineno
        if self.decorators is not None:
            lineno += sum(
                node.tolineno - node.lineno + 1 for node in self.decorators.nodes
            )

        return lineno

    @decorators_mod.cachedproperty
    def blockstart_tolineno(self):
        """The line on which the beginning of this block ends.

        :type: int
        """
        return self.args.tolineno

    def block_range(self, lineno):
        """Get a range from the given line number to where this node ends.

        :param lineno: Unused.
        :type lineno: int

        :returns: The range of line numbers that this node belongs to,
        :rtype: tuple(int, int)
        """
        return self.fromlineno, self.tolineno

    def getattr(self, name, context=None):
        """this method doesn't look in the instance_attrs dictionary since it's
        done by an Instance proxy at inference time.
        """
        if not name:
            raise AttributeInferenceError(target=self, attribute=name, context=context)

        found_attrs = []
        if name in self.instance_attrs:
            found_attrs = self.instance_attrs[name]
        if name in self.special_attributes:
            found_attrs.append(self.special_attributes.lookup(name))
        if found_attrs:
            return found_attrs
        raise AttributeInferenceError(target=self, attribute=name)

    def igetattr(self, name, context=None):
        """Inferred getattr, which returns an iterator of inferred statements."""
        try:
            return bases._infer_stmts(self.getattr(name, context), context, frame=self)
        except AttributeInferenceError as error:
            raise InferenceError(
                str(error), target=self, attribute=name, context=context
            ) from error

    def is_method(self):
        """Check if this function node represents a method.

        :returns: True if this is a method, False otherwise.
        :rtype: bool
        """
        # check we are defined in a ClassDef, because this is usually expected
        # (e.g. pylint...) when is_method() return True
        return self.type != "function" and isinstance(
            self.parent.frame(future=True), ClassDef
        )

    @decorators_mod.cached
    def decoratornames(self, context=None):
        """Get the qualified names of each of the decorators on this function.

        :param context:
            An inference context that can be passed to inference functions
        :returns: The names of the decorators.
        :rtype: set(str)
        """
        result = set()
        decoratornodes = []
        if self.decorators is not None:
            decoratornodes += self.decorators.nodes
        decoratornodes += self.extra_decorators
        for decnode in decoratornodes:
            try:
                for infnode in decnode.infer(context=context):
                    result.add(infnode.qname())
            except InferenceError:
                continue
        return result

    def is_bound(self):
        """Check if the function is bound to an instance or class.

        :returns: True if the function is bound to an instance or class,
            False otherwise.
        :rtype: bool
        """
        return self.type == "classmethod"

    def is_abstract(self, pass_is_abstract=True, any_raise_is_abstract=False):
        """Check if the method is abstract.

        A method is considered abstract if any of the following is true:
        * The only statement is 'raise NotImplementedError'
        * The only statement is 'raise <SomeException>' and any_raise_is_abstract is True
        * The only statement is 'pass' and pass_is_abstract is True
        * The method is annotated with abc.astractproperty/abc.abstractmethod

        :returns: True if the method is abstract, False otherwise.
        :rtype: bool
        """
        if self.decorators:
            for node in self.decorators.nodes:
                try:
                    inferred = next(node.infer())
                except (InferenceError, StopIteration):
                    continue
                if inferred and inferred.qname() in {
                    "abc.abstractproperty",
                    "abc.abstractmethod",
                }:
                    return True

        for child_node in self.body:
            if isinstance(child_node, node_classes.Raise):
                if any_raise_is_abstract:
                    return True
                if child_node.raises_not_implemented():
                    return True
            return pass_is_abstract and isinstance(child_node, node_classes.Pass)
        # empty function is the same as function with a single "pass" statement
        if pass_is_abstract:
            return True

    def is_generator(self):
        """Check if this is a generator function.

        :returns: True is this is a generator function, False otherwise.
        :rtype: bool
        """
        return bool(next(self._get_yield_nodes_skip_lambdas(), False))

    def infer_yield_result(self, context=None):
        """Infer what the function yields when called

        :returns: What the function yields
        :rtype: iterable(NodeNG or Uninferable) or None
        """
        # pylint: disable=not-an-iterable
        # https://github.com/PyCQA/astroid/issues/1015
        for yield_ in self.nodes_of_class(node_classes.Yield):
            if yield_.value is None:
                const = node_classes.Const(None)
                const.parent = yield_
                const.lineno = yield_.lineno
                yield const
            elif yield_.scope() == self:
                yield from yield_.value.infer(context=context)

    def infer_call_result(self, caller=None, context=None):
        """Infer what the function returns when called.

        :returns: What the function returns.
        :rtype: iterable(NodeNG or Uninferable) or None
        """
        if self.is_generator():
            if isinstance(self, AsyncFunctionDef):
                generator_cls = bases.AsyncGenerator
            else:
                generator_cls = bases.Generator
            result = generator_cls(self, generator_initial_context=context)
            yield result
            return
        # This is really a gigantic hack to work around metaclass generators
        # that return transient class-generating functions. Pylint's AST structure
        # cannot handle a base class object that is only used for calling __new__,
        # but does not contribute to the inheritance structure itself. We inject
        # a fake class into the hierarchy here for several well-known metaclass
        # generators, and filter it out later.
        if (
            self.name == "with_metaclass"
            and len(self.args.args) == 1
            and self.args.vararg is not None
        ):
            metaclass = next(caller.args[0].infer(context), None)
            if isinstance(metaclass, ClassDef):
                try:
                    class_bases = [next(arg.infer(context)) for arg in caller.args[1:]]
                except StopIteration as e:
                    raise InferenceError(node=caller.args[1:], context=context) from e
                new_class = ClassDef(name="temporary_class")
                new_class.hide = True
                new_class.parent = self
                new_class.postinit(
                    bases=[base for base in class_bases if base != util.Uninferable],
                    body=[],
                    decorators=[],
                    metaclass=metaclass,
                )
                yield new_class
                return
        returns = self._get_return_nodes_skip_functions()

        first_return = next(returns, None)
        if not first_return:
            if self.body:
                if self.is_abstract(pass_is_abstract=True, any_raise_is_abstract=True):
                    yield util.Uninferable
                else:
                    yield node_classes.Const(None)
                return

            raise InferenceError("The function does not have any return statements")

        for returnnode in itertools.chain((first_return,), returns):
            if returnnode.value is None:
                yield node_classes.Const(None)
            else:
                try:
                    yield from returnnode.value.infer(context)
                except InferenceError:
                    yield util.Uninferable

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`FunctionDef` this is always ``True``.
        :rtype: bool
        """
        return True

    def get_children(self):
        if self.decorators is not None:
            yield self.decorators

        yield self.args

        if self.returns is not None:
            yield self.returns

        yield from self.body

    def scope_lookup(self, node, name, offset=0):
        """Lookup where the given name is assigned."""
        if name == "__class__":
            # __class__ is an implicit closure reference created by the compiler
            # if any methods in a class body refer to either __class__ or super.
            # In our case, we want to be able to look it up in the current scope
            # when `__class__` is being used.
            frame = self.parent.frame(future=True)
            if isinstance(frame, ClassDef):
                return self, [frame]
        return super().scope_lookup(node, name, offset)

    def frame(self: T, *, future: Literal[None, True] = None) -> T:
        """The node's frame node.

        A frame node is a :class:`Module`, :class:`FunctionDef`,
        :class:`ClassDef` or :class:`Lambda`.

        :returns: The node itself.
        """
        return self


class AsyncFunctionDef(FunctionDef):
    """Class representing an :class:`ast.FunctionDef` node.

    A :class:`AsyncFunctionDef` is an asynchronous function
    created with the `async` keyword.

    >>> import astroid
    >>> node = astroid.extract_node('''
    async def func(things):
        async for thing in things:
            print(thing)
    ''')
    >>> node
    <AsyncFunctionDef.func l.2 at 0x7f23b2e416d8>
    >>> node.body[0]
    <AsyncFor l.3 at 0x7f23b2e417b8>
    """


def _rec_get_names(args, names: Optional[List[str]] = None) -> List[str]:
    """return a list of all argument names"""
    if names is None:
        names = []
    for arg in args:
        if isinstance(arg, node_classes.Tuple):
            _rec_get_names(arg.elts, names)
        else:
            names.append(arg.name)
    return names


def _is_metaclass(klass, seen=None):
    """Return if the given class can be
    used as a metaclass.
    """
    if klass.name == "type":
        return True
    if seen is None:
        seen = set()
    for base in klass.bases:
        try:
            for baseobj in base.infer():
                baseobj_name = baseobj.qname()
                if baseobj_name in seen:
                    continue

                seen.add(baseobj_name)
                if isinstance(baseobj, bases.Instance):
                    # not abstract
                    return False
                if baseobj is util.Uninferable:
                    continue
                if baseobj is klass:
                    continue
                if not isinstance(baseobj, ClassDef):
                    continue
                if baseobj._type == "metaclass":
                    return True
                if _is_metaclass(baseobj, seen):
                    return True
        except InferenceError:
            continue
    return False


def _class_type(klass, ancestors=None):
    """return a ClassDef node type to differ metaclass and exception
    from 'regular' classes
    """
    # XXX we have to store ancestors in case we have an ancestor loop
    if klass._type is not None:
        return klass._type
    if _is_metaclass(klass):
        klass._type = "metaclass"
    elif klass.name.endswith("Exception"):
        klass._type = "exception"
    else:
        if ancestors is None:
            ancestors = set()
        klass_name = klass.qname()
        if klass_name in ancestors:
            # XXX we are in loop ancestors, and have found no type
            klass._type = "class"
            return "class"
        ancestors.add(klass_name)
        for base in klass.ancestors(recurs=False):
            name = _class_type(base, ancestors)
            if name != "class":
                if name == "metaclass" and not _is_metaclass(klass):
                    # don't propagate it if the current class
                    # can't be a metaclass
                    continue
                klass._type = base.type
                break
    if klass._type is None:
        klass._type = "class"
    return klass._type


def get_wrapping_class(node):
    """Get the class that wraps the given node.

    We consider that a class wraps a node if the class
    is a parent for the said node.

    :returns: The class that wraps the given node
    :rtype: ClassDef or None
    """

    klass = node.frame(future=True)
    while klass is not None and not isinstance(klass, ClassDef):
        if klass.parent is None:
            klass = None
        else:
            klass = klass.parent.frame(future=True)
    return klass


class ClassDef(mixins.FilterStmtsMixin, LocalsDictNodeNG, node_classes.Statement):
    """Class representing an :class:`ast.ClassDef` node.

    >>> import astroid
    >>> node = astroid.extract_node('''
    class Thing:
        def my_meth(self, arg):
            return arg + self.offset
    ''')
    >>> node
    <ClassDef.Thing l.2 at 0x7f23b2e9e748>
    """

    # some of the attributes below are set by the builder module or
    # by a raw factories

    # a dictionary of class instances attributes
    _astroid_fields = ("decorators", "bases", "keywords", "body")  # name

    decorators = None
    """The decorators that are applied to this class.

    :type: Decorators or None
    """
    special_attributes = ClassModel()
    """The names of special attributes that this class has.

    :type: objectmodel.ClassModel
    """

    _type = None
    _metaclass_hack = False
    hide = False
    type = property(
        _class_type,
        doc=(
            "The class type for this node.\n\n"
            "Possible values are: class, metaclass, exception.\n\n"
            ":type: str"
        ),
    )
    _other_fields = ("name", "doc")
    _other_other_fields = ("locals", "_newstyle")
    _newstyle = None

    def __init__(
        self,
        name=None,
        doc=None,
        lineno=None,
        col_offset=None,
        parent=None,
        *,
        end_lineno=None,
        end_col_offset=None,
    ):
        """
        :param name: The name of the class.
        :type name: str or None

        :param doc: The function's docstring.
        :type doc: str or None

        :param lineno: The line that this node appears on in the source code.
        :type lineno: int or None

        :param col_offset: The column that this node appears on in the
            source code.
        :type col_offset: int or None

        :param parent: The parent node in the syntax tree.
        :type parent: NodeNG or None

        :param end_lineno: The last line this node appears on in the source code.
        :type end_lineno: Optional[int]

        :param end_col_offset: The end column this node appears on in the
            source code. Note: This is after the last symbol.
        :type end_col_offset: Optional[int]
        """
        self.instance_attrs = {}
        self.locals = {}
        """A map of the name of a local variable to the node defining it.

        :type: dict(str, NodeNG)
        """

        self.keywords = []
        """The keywords given to the class definition.

        This is usually for :pep:`3115` style metaclass declaration.

        :type: list(Keyword) or None
        """

        self.bases = []
        """What the class inherits from.

        :type: list(NodeNG)
        """

        self.body = []
        """The contents of the class body.

        :type: list(NodeNG)
        """

        self.name = name
        """The name of the class.

        :type name: str or None
        """

        self.doc = doc
        """The class' docstring.

        :type doc: str or None
        """

        super().__init__(
            lineno=lineno,
            col_offset=col_offset,
            end_lineno=end_lineno,
            end_col_offset=end_col_offset,
            parent=parent,
        )
        if parent is not None:
            parent.frame(future=True).set_local(name, self)

        for local_name, node in self.implicit_locals():
            self.add_local_node(node, local_name)

    def implicit_parameters(self):
        return 1

    def implicit_locals(self):
        """Get implicitly defined class definition locals.

        :returns: the the name and Const pair for each local
        :rtype: tuple(tuple(str, node_classes.Const), ...)
        """
        locals_ = (("__module__", self.special_attributes.attr___module__),)
        # __qualname__ is defined in PEP3155
        locals_ += (("__qualname__", self.special_attributes.attr___qualname__),)
        return locals_

    # pylint: disable=redefined-outer-name
    def postinit(
        self, bases, body, decorators, newstyle=None, metaclass=None, keywords=None
    ):
        """Do some setup after initialisation.

        :param bases: What the class inherits from.
        :type bases: list(NodeNG)

        :param body: The contents of the class body.
        :type body: list(NodeNG)

        :param decorators: The decorators that are applied to this class.
        :type decorators: Decorators or None

        :param newstyle: Whether this is a new style class or not.
        :type newstyle: bool or None

        :param metaclass: The metaclass of this class.
        :type metaclass: NodeNG or None

        :param keywords: The keywords given to the class definition.
        :type keywords: list(Keyword) or None
        """
        if keywords is not None:
            self.keywords = keywords
        self.bases = bases
        self.body = body
        self.decorators = decorators
        if newstyle is not None:
            self._newstyle = newstyle
        if metaclass is not None:
            self._metaclass = metaclass

    def _newstyle_impl(self, context=None):
        if context is None:
            context = InferenceContext()
        if self._newstyle is not None:
            return self._newstyle
        for base in self.ancestors(recurs=False, context=context):
            if base._newstyle_impl(context):
                self._newstyle = True
                break
        klass = self.declared_metaclass()
        # could be any callable, we'd need to infer the result of klass(name,
        # bases, dict).  punt if it's not a class node.
        if klass is not None and isinstance(klass, ClassDef):
            self._newstyle = klass._newstyle_impl(context)
        if self._newstyle is None:
            self._newstyle = False
        return self._newstyle

    _newstyle = None
    newstyle = property(
        _newstyle_impl,
        doc=("Whether this is a new style class or not\n\n" ":type: bool or None"),
    )

    @decorators_mod.cachedproperty
    def fromlineno(self) -> Optional[int]:
        """The first line that this node appears on in the source code."""
        if not PY38_PLUS:
            # For Python < 3.8 the lineno is the line number of the first decorator.
            # We want the class statement lineno. Similar to 'FunctionDef.fromlineno'
            lineno = self.lineno
            if self.decorators is not None:
                lineno += sum(
                    node.tolineno - node.lineno + 1 for node in self.decorators.nodes
                )

            return lineno
        return super().fromlineno

    @decorators_mod.cachedproperty
    def blockstart_tolineno(self):
        """The line on which the beginning of this block ends.

        :type: int
        """
        if self.bases:
            return self.bases[-1].tolineno

        return self.fromlineno

    def block_range(self, lineno):
        """Get a range from the given line number to where this node ends.

        :param lineno: Unused.
        :type lineno: int

        :returns: The range of line numbers that this node belongs to,
        :rtype: tuple(int, int)
        """
        return self.fromlineno, self.tolineno

    def pytype(self):
        """Get the name of the type that this node represents.

        :returns: The name of the type.
        :rtype: str
        """
        if self.newstyle:
            return "builtins.type"
        return "builtins.classobj"

    def display_type(self):
        """A human readable type of this node.

        :returns: The type of this node.
        :rtype: str
        """
        return "Class"

    def callable(self):
        """Whether this node defines something that is callable.

        :returns: True if this defines something that is callable,
            False otherwise.
            For a :class:`ClassDef` this is always ``True``.
        :rtype: bool
        """
        return True

    def is_subtype_of(self, type_name, context=None):
        """Whether this class is a subtype of the given type.

        :param type_name: The name of the type of check against.
        :type type_name: str

        :returns: True if this class is a subtype of the given type,
            False otherwise.
        :rtype: bool
        """
        if self.qname() == type_name:
            return True

        return any(anc.qname() == type_name for anc in self.ancestors(context=context))

    def _infer_type_call(self, caller, context):
        try:
            name_node = next(caller.args[0].infer(context))
        except StopIteration as e:
            raise InferenceError(node=caller.args[0], context=context) from e
        if isinstance(name_node, node_classes.Const) and isinstance(
            name_node.value, str
        ):
            name = name_node.value
        else:
            return util.Uninferable

        result = ClassDef(name, None)

        # Get the bases of the class.
        try:
            class_bases = next(caller.args[1].infer(context))
        except StopIteration as e:
            raise InferenceError(node=caller.args[1], context=context) from e
        if isinstance(class_bases, (node_classes.Tuple, node_classes.List)):
            bases = []
            for base in class_bases.itered():
                inferred = next(base.infer(context=context), None)
                if inferred:
                    bases.append(
                        node_classes.EvaluatedObject(original=base, value=inferred)
                    )
            result.bases = bases
        else:
            # There is currently no AST node that can represent an 'unknown'
            # node (Uninferable is not an AST node), therefore we simply return Uninferable here
            # although we know at least the name of the class.
            return util.Uninferable

        # Get the members of the class
        try:
            members = next(caller.args[2].infer(context))
        except (InferenceError, StopIteration):
            members = None

        if members and isinstance(members, node_classes.Dict):
            for attr, value in members.items:
                if isinstance(attr, node_classes.Const) and isinstance(attr.value, str):
                    result.locals[attr.value] = [value]

        result.parent = caller.parent
        return result

    def infer_call_result(self, caller, context=None):
        """infer what a class is returning when called"""
        if self.is_subtype_of("builtins.type", context) and len(caller.args) == 3:
            result = self._infer_type_call(caller, context)
            yield result
            return

        dunder_call = None
        try:
            metaclass = self.metaclass(context=context)
            if metaclass is not None:
                dunder_call = next(metaclass.igetattr("__call__", context))
        except (AttributeInferenceError, StopIteration):
            pass

        if dunder_call and dunder_call.qname() != "builtins.type.__call__":
            # Call type.__call__ if not set metaclass
            # (since type is the default metaclass)
            context = bind_context_to_node(context, self)
            context.callcontext.callee = dunder_call
            yield from dunder_call.infer_call_result(caller, context)
        else:
            yield self.instantiate_class()

    def scope_lookup(self, node, name, offset=0):
        """Lookup where the given name is assigned.

        :param node: The node to look for assignments up to.
            Any assignments after the given node are ignored.
        :type node: NodeNG

        :param name: The name to find assignments for.
        :type name: str

        :param offset: The line offset to filter statements up to.
        :type offset: int

        :returns: This scope node and the list of assignments associated to the
            given name according to the scope where it has been found (locals,
            globals or builtin).
        :rtype: tuple(str, list(NodeNG))
        """
        # If the name looks like a builtin name, just try to look
        # into the upper scope of this class. We might have a
        # decorator that it's poorly named after a builtin object
        # inside this class.
        lookup_upper_frame = (
            isinstance(node.parent, node_classes.Decorators)
            and name in AstroidManager().builtins_module
        )
        if (
            any(node == base or base.parent_of(node) for base in self.bases)
            or lookup_upper_frame
        ):
            # Handle the case where we have either a name
            # in the bases of a class, which exists before
            # the actual definition or the case where we have
            # a Getattr node, with that name.
            #
            # name = ...
            # class A(name):
            #     def name(self): ...
            #
            # import name
            # class A(name.Name):
            #     def name(self): ...

            frame = self.parent.frame(future=True)
            # line offset to avoid that class A(A) resolve the ancestor to
            # the defined class
            offset = -1
        else:
            frame = self
        return frame._scope_lookup(node, name, offset)

    @property
    def basenames(self):
        """The names of the parent classes

        Names are given in the order they appear in the class definition.

        :type: list(str)
        """
        return [bnode.as_string() for bnode in self.bases]

    def ancestors(self, recurs=True, context=None):
        """Iterate over the base classes in prefixed depth first order.

        :param recurs: Whether to recurse or return direct ancestors only.
        :type recurs: bool

        :returns: The base classes
        :rtype: iterable(NodeNG)
        """
        # FIXME: should be possible to choose the resolution order
        # FIXME: inference make infinite loops possible here
        yielded = {self}
        if context is None:
            context = InferenceContext()
        if not self.bases and self.qname() != "builtins.object":
            yield builtin_lookup("object")[1][0]
            return

        for stmt in self.bases:
            with context.restore_path():
                try:
                    for baseobj in stmt.infer(context):
                        if not isinstance(baseobj, ClassDef):
                            if isinstance(baseobj, bases.Instance):
                                baseobj = baseobj._proxied
                            else:
                                continue
                        if not baseobj.hide:
                            if baseobj in yielded:
                                continue
                            yielded.add(baseobj)
                            yield baseobj
                        if not recurs:
                            continue
                        for grandpa in baseobj.ancestors(recurs=True, context=context):
                            if grandpa is self:
                                # This class is the ancestor of itself.
                                break
                            if grandpa in yielded:
                                continue
                            yielded.add(grandpa)
                            yield grandpa
                except InferenceError:
                    continue

    def local_attr_ancestors(self, name, context=None):
        """Iterate over the parents that define the given name.

        :param name: The name to find definitions for.
        :type name: str

        :returns: The parents that define the given name.
        :rtype: iterable(NodeNG)
        """
        # Look up in the mro if we can. This will result in the
        # attribute being looked up just as Python does it.
        try:
            ancestors = self.mro(context)[1:]
        except MroError:
            # Fallback to use ancestors, we can't determine
            # a sane MRO.
            ancestors = self.ancestors(context=context)
        for astroid in ancestors:
            if name in astroid:
                yield astroid

    def instance_attr_ancestors(self, name, context=None):
        """Iterate over the parents that define the given name as an attribute.

        :param name: The name to find definitions for.
        :type name: str

        :returns: The parents that define the given name as
            an instance attribute.
        :rtype: iterable(NodeNG)
        """
        for astroid in self.ancestors(context=context):
            if name in astroid.instance_attrs:
                yield astroid

    def has_base(self, node):
        """Whether this class directly inherits from the given node.

        :param node: The node to check for.
        :type node: NodeNG

        :returns: True if this class directly inherits from the given node.
        :rtype: bool
        """
        return node in self.bases

    def local_attr(self, name, context=None):
        """Get the list of assign nodes associated to the given name.

        Assignments are looked for in both this class and in parents.

        :returns: The list of assignments to the given name.
        :rtype: list(NodeNG)

        :raises AttributeInferenceError: If no attribute with this name
            can be found in this class or parent classes.
        """
        result = []
        if name in self.locals:
            result = self.locals[name]
        else:
            class_node = next(self.local_attr_ancestors(name, context), None)
            if class_node:
                result = class_node.locals[name]
        result = [n for n in result if not isinstance(n, node_classes.DelAttr)]
        if result:
            return result
        raise AttributeInferenceError(target=self, attribute=name, context=context)

    def instance_attr(self, name, context=None):
        """Get the list of nodes associated to the given attribute name.

        Assignments are looked for in both this class and in parents.

        :returns: The list of assignments to the given name.
        :rtype: list(NodeNG)

        :raises AttributeInferenceError: If no attribute with this name
            can be found in this class or parent classes.
        """
        # Return a copy, so we don't modify self.instance_attrs,
        # which could lead to infinite loop.
        values = list(self.instance_attrs.get(name, []))
        # get all values from parents
        for class_node in self.instance_attr_ancestors(name, context):
            values += class_node.instance_attrs[name]
        values = [n for n in values if not isinstance(n, node_classes.DelAttr)]
        if values:
            return values
        raise AttributeInferenceError(target=self, attribute=name, context=context)

    def instantiate_class(self):
        """Get an :class:`Instance` of the :class:`ClassDef` node.

        :returns: An :class:`Instance` of the :class:`ClassDef` node,
            or self if this is not possible.
        :rtype: Instance or ClassDef
        """
        try:
            if any(cls.name in EXCEPTION_BASE_CLASSES for cls in self.mro()):
                # Subclasses of exceptions can be exception instances
                return objects.ExceptionInstance(self)
        except MroError:
            pass
        return bases.Instance(self)

    def getattr(self, name, context=None, class_context=True):
        """Get an attribute from this class, using Python's attribute semantic.

        This method doesn't look in the :attr:`instance_attrs` dictionary
        since it is done by an :class:`Instance` proxy at inference time.
        It may return an :class:`Uninferable` object if
        the attribute has not been
        found, but a ``__getattr__`` or ``__getattribute__`` method is defined.
        If ``class_context`` is given, then it is considered that the
        attribute is accessed from a class context,
        e.g. ClassDef.attribute, otherwise it might have been accessed
        from an instance as well. If ``class_context`` is used in that
        case, then a lookup in the implicit metaclass and the explicit
        metaclass will be done.

        :param name: The attribute to look for.
        :type name: str

        :param class_context: Whether the attribute can be accessed statically.
        :type class_context: bool

        :returns: The attribute.
        :rtype: list(NodeNG)

        :raises AttributeInferenceError: If the attribute cannot be inferred.
        """
        if not name:
            raise AttributeInferenceError(target=self, attribute=name, context=context)

        values = self.locals.get(name, [])
        if name in self.special_attributes and class_context and not values:
            result = [self.special_attributes.lookup(name)]
            if name == "__bases__":
                # Need special treatment, since they are mutable
                # and we need to return all the values.
                result += values
            return result

        # don't modify the list in self.locals!
        values = list(values)
        for classnode in self.ancestors(recurs=True, context=context):
            values += classnode.locals.get(name, [])

        if class_context:
            values += self._metaclass_lookup_attribute(name, context)

        if not values:
            raise AttributeInferenceError(target=self, attribute=name, context=context)

        # Look for AnnAssigns, which are not attributes in the purest sense.
        for value in values:
            if isinstance(value, node_classes.AssignName):
                stmt = value.statement(future=True)
                if isinstance(stmt, node_classes.AnnAssign) and stmt.value is None:
                    raise AttributeInferenceError(
                        target=self, attribute=name, context=context
                    )
        return values

    def _metaclass_lookup_attribute(self, name, context):
        """Search the given name in the implicit and the explicit metaclass."""
        attrs = set()
        implicit_meta = self.implicit_metaclass()
        context = copy_context(context)
        metaclass = self.metaclass(context=context)
        for cls in (implicit_meta, metaclass):
            if cls and cls != self and isinstance(cls, ClassDef):
                cls_attributes = self._get_attribute_from_metaclass(cls, name, context)
                attrs.update(set(cls_attributes))
        return attrs

    def _get_attribute_from_metaclass(self, cls, name, context):
        try:
            attrs = cls.getattr(name, context=context, class_context=True)
        except AttributeInferenceError:
            return

        for attr in bases._infer_stmts(attrs, context, frame=cls):
            if not isinstance(attr, FunctionDef):
                yield attr
                continue

            if isinstance(attr, objects.Property):
                yield attr
                continue
            if attr.type == "classmethod":
                # If the method is a classmethod, then it will
                # be bound to the metaclass, not to the class
                # from where the attribute is retrieved.
                # get_wrapping_class could return None, so just
                # default to the current class.
                frame = get_wrapping_class(attr) or self
                yield bases.BoundMethod(attr, frame)
            elif attr.type == "staticmethod":
                yield attr
            else:
                yield bases.BoundMethod(attr, self)

    def igetattr(self, name, context=None, class_context=True):
        """Infer the possible values of the given variable.

        :param name: The name of the variable to infer.
        :type name: str

        :returns: The inferred possible values.
        :rtype: iterable(NodeNG or Uninferable)
        """
        # set lookup name since this is necessary to infer on import nodes for
        # instance
        context = copy_context(context)
        context.lookupname = name

        metaclass = self.metaclass(context=context)
        try:
            attributes = self.getattr(name, context, class_context=class_context)
            # If we have more than one attribute, make sure that those starting from
            # the second one are from the same scope. This is to account for modifications
            # to the attribute happening *after* the attribute's definition (e.g. AugAssigns on lists)
            if len(attributes) > 1:
                first_attr, attributes = attributes[0], attributes[1:]
                first_scope = first_attr.scope()
                attributes = [first_attr] + [
                    attr
                    for attr in attributes
                    if attr.parent and attr.parent.scope() == first_scope
                ]

            for inferred in bases._infer_stmts(attributes, context, frame=self):
                # yield Uninferable object instead of descriptors when necessary
                if not isinstance(inferred, node_classes.Const) and isinstance(
                    inferred, bases.Instance
                ):
                    try:
                        inferred._proxied.getattr("__get__", context)
                    except AttributeInferenceError:
                        yield inferred
                    else:
                        yield util.Uninferable
                elif isinstance(inferred, objects.Property):
                    function = inferred.function
                    if not class_context:
                        # Through an instance so we can solve the property
                        yield from function.infer_call_result(
                            caller=self, context=context
                        )
                    # If we're in a class context, we need to determine if the property
                    # was defined in the metaclass (a derived class must be a subclass of
                    # the metaclass of all its bases), in which case we can resolve the
                    # property. If not, i.e. the property is defined in some base class
                    # instead, then we return the property object
                    elif metaclass and function.parent.scope() is metaclass:
                        # Resolve a property as long as it is not accessed through
                        # the class itself.
                        yield from function.infer_call_result(
                            caller=self, context=context
                        )
                    else:
                        yield inferred
                else:
                    yield function_to_method(inferred, self)
        except AttributeInferenceError as error:
            if not name.startswith("__") and self.has_dynamic_getattr(context):
                # class handle some dynamic attributes, return a Uninferable object
                yield util.Uninferable
            else:
                raise InferenceError(
                    str(error), target=self, attribute=name, context=context
                ) from error

    def has_dynamic_getattr(self, context=None):
        """Check if the class has a custom __getattr__ or __getattribute__.

        If any such method is found and it is not from
        builtins, nor from an extension module, then the function
        will return True.

        :returns: True if the class has a custom
            __getattr__ or __getattribute__, False otherwise.
        :rtype: bool
        """

        def _valid_getattr(node):
            root = node.root()
            return root.name != "builtins" and getattr(root, "pure_python", None)

        try:
            return _valid_getattr(self.getattr("__getattr__", context)[0])
        except AttributeInferenceError:
            # if self.newstyle: XXX cause an infinite recursion error
            try:
                getattribute = self.getattr("__getattribute__", context)[0]
                return _valid_getattr(getattribute)
            except AttributeInferenceError:
                pass
        return False

    def getitem(self, index, context=None):
        """Return the inference of a subscript.

        This is basically looking up the method in the metaclass and calling it.

        :returns: The inferred value of a subscript to this class.
        :rtype: NodeNG

        :raises AstroidTypeError: If this class does not define a
            ``__getitem__`` method.
        """
        try:
            methods = lookup(self, "__getitem__")
        except AttributeInferenceError as exc:
            if isinstance(self, ClassDef):
                # subscripting a class definition may be
                # achieved thanks to __class_getitem__ method
                # which is a classmethod defined in the class
                # that supports subscript and not in the metaclass
                try:
                    methods = self.getattr("__class_getitem__")
                    # Here it is assumed that the __class_getitem__ node is
                    # a FunctionDef. One possible improvement would be to deal
                    # with more generic inference.
                except AttributeInferenceError:
                    raise AstroidTypeError(node=self, context=context) from exc
            else:
                raise AstroidTypeError(node=self, context=context) from exc

        method = methods[0]

        # Create a new callcontext for providing index as an argument.
        new_context = bind_context_to_node(context, self)
        new_context.callcontext = CallContext(args=[index], callee=method)

        try:
            return next(method.infer_call_result(self, new_context), util.Uninferable)
        except AttributeError:
            # Starting with python3.9, builtin types list, dict etc...
            # are subscriptable thanks to __class_getitem___ classmethod.
            # However in such case the method is bound to an EmptyNode and
            # EmptyNode doesn't have infer_call_result method yielding to
            # AttributeError
            if (
                isinstance(method, node_classes.EmptyNode)
                and self.name in {"list", "dict", "set", "tuple", "frozenset"}
                and PY39_PLUS
            ):
                return self
            raise
        except InferenceError:
            return util.Uninferable

    def methods(self):
        """Iterate over all of the method defined in this class and its parents.

        :returns: The methods defined on the class.
        :rtype: iterable(FunctionDef)
        """
        done = {}
        for astroid in itertools.chain(iter((self,)), self.ancestors()):
            for meth in astroid.mymethods():
                if meth.name in done:
                    continue
                done[meth.name] = None
                yield meth

    def mymethods(self):
        """Iterate over all of the method defined in this class only.

        :returns: The methods defined on the class.
        :rtype: iterable(FunctionDef)
        """
        for member in self.values():
            if isinstance(member, FunctionDef):
                yield member

    def implicit_metaclass(self):
        """Get the implicit metaclass of the current class.

        For newstyle classes, this will return an instance of builtins.type.
        For oldstyle classes, it will simply return None, since there's
        no implicit metaclass there.

        :returns: The metaclass.
        :rtype: builtins.type or None
        """
        if self.newstyle:
            return builtin_lookup("type")[1][0]
        return None

    _metaclass = None

    def declared_metaclass(self, context=None):
        """Return the explicit declared metaclass for the current class.

        An explicit declared metaclass is defined
        either by passing the ``metaclass`` keyword argument
        in the class definition line (Python 3) or (Python 2) by
        having a ``__metaclass__`` class attribute, or if there are
        no explicit bases but there is a global ``__metaclass__`` variable.

        :returns: The metaclass of this class,
            or None if one could not be found.
        :rtype: NodeNG or None
        """
        for base in self.bases:
            try:
                for baseobj in base.infer(context=context):
                    if isinstance(baseobj, ClassDef) and baseobj.hide:
                        self._metaclass = baseobj._metaclass
                        self._metaclass_hack = True
                        break
            except InferenceError:
                pass

        if self._metaclass:
            # Expects this from Py3k TreeRebuilder
            try:
                return next(
                    node
                    for node in self._metaclass.infer(context=context)
                    if node is not util.Uninferable
                )
            except (InferenceError, StopIteration):
                return None

        return None

    def _find_metaclass(self, seen=None, context=None):
        if seen is None:
            seen = set()
        seen.add(self)

        klass = self.declared_metaclass(context=context)
        if klass is None:
            for parent in self.ancestors(context=context):
                if parent not in seen:
                    klass = parent._find_metaclass(seen)
                    if klass is not None:
                        break
        return klass

    def metaclass(self, context=None):
        """Get the metaclass of this class.

        If this class does not define explicitly a metaclass,
        then the first defined metaclass in ancestors will be used
        instead.

        :returns: The metaclass of this class.
        :rtype: NodeNG or None
        """
        return self._find_metaclass(context=context)

    def has_metaclass_hack(self):
        return self._metaclass_hack

    def _islots(self):
        """Return an iterator with the inferred slots."""
        if "__slots__" not in self.locals:
            return None
        for slots in self.igetattr("__slots__"):
            # check if __slots__ is a valid type
            for meth in ITER_METHODS:
                try:
                    slots.getattr(meth)
                    break
                except AttributeInferenceError:
                    continue
            else:
                continue

            if isinstance(slots, node_classes.Const):
                # a string. Ignore the following checks,
                # but yield the node, only if it has a value
                if slots.value:
                    yield slots
                continue
            if not hasattr(slots, "itered"):
                # we can't obtain the values, maybe a .deque?
                continue

            if isinstance(slots, node_classes.Dict):
                values = [item[0] for item in slots.items]
            else:
                values = slots.itered()
            if values is util.Uninferable:
                continue
            if not values:
                # Stop the iteration, because the class
                # has an empty list of slots.
                return values

            for elt in values:
                try:
                    for inferred in elt.infer():
                        if inferred is util.Uninferable:
                            continue
                        if not isinstance(
                            inferred, node_classes.Const
                        ) or not isinstance(inferred.value, str):
                            continue
                        if not inferred.value:
                            continue
                        yield inferred
                except InferenceError:
                    continue

        return None

    def _slots(self):
        if not self.newstyle:
            raise NotImplementedError(
                "The concept of slots is undefined for old-style classes."
            )

        slots = self._islots()
        try:
            first = next(slots)
        except StopIteration as exc:
            # The class doesn't have a __slots__ definition or empty slots.
            if exc.args and exc.args[0] not in ("", None):
                return exc.args[0]
            return None
        return [first] + list(slots)

    # Cached, because inferring them all the time is expensive
    @decorators_mod.cached
    def slots(self):
        """Get all the slots for this node.

        :returns: The names of slots for this class.
            If the class doesn't define any slot, through the ``__slots__``
            variable, then this function will return a None.
            Also, it will return None in the case the slots were not inferred.
        :rtype: list(str) or None
        """

        def grouped_slots(
            mro: List["ClassDef"],
        ) -> typing.Iterator[Optional[node_classes.NodeNG]]:
            # Not interested in object, since it can't have slots.
            for cls in mro[:-1]:
                try:
                    cls_slots = cls._slots()
                except NotImplementedError:
                    continue
                if cls_slots is not None:
                    yield from cls_slots
                else:
                    yield None

        if not self.newstyle:
            raise NotImplementedError(
                "The concept of slots is undefined for old-style classes."
            )

        try:
            mro = self.mro()
        except MroError as e:
            raise NotImplementedError(
                "Cannot get slots while parsing mro fails."
            ) from e

        slots = list(grouped_slots(mro))
        if not all(slot is not None for slot in slots):
            return None

        return sorted(set(slots), key=lambda item: item.value)

    def _inferred_bases(self, context=None):
        # Similar with .ancestors, but the difference is when one base is inferred,
        # only the first object is wanted. That's because
        # we aren't interested in superclasses, as in the following
        # example:
        #
        # class SomeSuperClass(object): pass
        # class SomeClass(SomeSuperClass): pass
        # class Test(SomeClass): pass
        #
        # Inferring SomeClass from the Test's bases will give
        # us both SomeClass and SomeSuperClass, but we are interested
        # only in SomeClass.

        if context is None:
            context = InferenceContext()
        if not self.bases and self.qname() != "builtins.object":
            yield builtin_lookup("object")[1][0]
            return

        for stmt in self.bases:
            try:
                # Find the first non-None inferred base value
                baseobj = next(
                    b
                    for b in stmt.infer(context=context.clone())
                    if not (isinstance(b, Const) and b.value is None)
                )
            except (InferenceError, StopIteration):
                continue
            if isinstance(baseobj, bases.Instance):
                baseobj = baseobj._proxied
            if not isinstance(baseobj, ClassDef):
                continue
            if not baseobj.hide:
                yield baseobj
            else:
                yield from baseobj.bases

    def _compute_mro(self, context=None):
        inferred_bases = list(self._inferred_bases(context=context))
        bases_mro = []
        for base in inferred_bases:
            if base is self:
                continue

            try:
                mro = base._compute_mro(context=context)
                bases_mro.append(mro)
            except NotImplementedError:
                # Some classes have in their ancestors both newstyle and
                # old style classes. For these we can't retrieve the .mro,
                # although in Python it's possible, since the class we are
                # currently working is in fact new style.
                # So, we fallback to ancestors here.
                ancestors = list(base.ancestors(context=context))
                bases_mro.append(ancestors)

        unmerged_mro = [[self]] + bases_mro + [inferred_bases]
        unmerged_mro = list(clean_duplicates_mro(unmerged_mro, self, context))
        clean_typing_generic_mro(unmerged_mro)
        return _c3_merge(unmerged_mro, self, context)

    def mro(self, context=None) -> List["ClassDef"]:
        """Get the method resolution order, using C3 linearization.

        :returns: The list of ancestors, sorted by the mro.
        :rtype: list(NodeNG)
        :raises DuplicateBasesError: Duplicate bases in the same class base
        :raises InconsistentMroError: A class' MRO is inconsistent
        """
        return self._compute_mro(context=context)

    def bool_value(self, context=None):
        """Determine the boolean value of this node.

        :returns: The boolean value of this node.
            For a :class:`ClassDef` this is always ``True``.
        :rtype: bool
        """
        return True

    def get_children(self):
        if self.decorators is not None:
            yield self.decorators

        yield from self.bases
        if self.keywords is not None:
            yield from self.keywords
        yield from self.body

    @decorators_mod.cached
    def _get_assign_nodes(self):
        children_assign_nodes = (
            child_node._get_assign_nodes() for child_node in self.body
        )
        return list(itertools.chain.from_iterable(children_assign_nodes))

    def frame(self: T, *, future: Literal[None, True] = None) -> T:
        """The node's frame node.

        A frame node is a :class:`Module`, :class:`FunctionDef`,
        :class:`ClassDef` or :class:`Lambda`.

        :returns: The node itself.
        """
        return self
