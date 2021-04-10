# Copyright (c) 2017-2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 David Euresti <github@euresti.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
# Copyright (c) 2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>

"""Astroid hooks for typing.py support."""
import sys
import typing
from functools import partial

from astroid import (
    MANAGER,
    UseInferenceDefault,
    extract_node,
    inference_tip,
    node_classes,
    nodes,
    context,
    InferenceError,
    AttributeInferenceError,
)
import astroid

PY37 = sys.version_info[:2] >= (3, 7)
PY39 = sys.version_info[:2] >= (3, 9)

TYPING_NAMEDTUPLE_BASENAMES = {"NamedTuple", "typing.NamedTuple"}
TYPING_TYPEVARS = {"TypeVar", "NewType"}
TYPING_TYPEVARS_QUALIFIED = {"typing.TypeVar", "typing.NewType"}
TYPING_TYPE_TEMPLATE = """
class Meta(type):
    def __getitem__(self, item):
        return self

    @property
    def __args__(self):
        return ()

class {0}(metaclass=Meta):
    pass
"""
TYPING_MEMBERS = set(typing.__all__)

TYPING_ALIAS = frozenset(
    (
        "typing.Hashable",
        "typing.Awaitable",
        "typing.Coroutine",
        "typing.AsyncIterable",
        "typing.AsyncIterator",
        "typing.Iterable",
        "typing.Iterator",
        "typing.Reversible",
        "typing.Sized",
        "typing.Container",
        "typing.Collection",
        "typing.Callable",
        "typing.AbstractSet",
        "typing.MutableSet",
        "typing.Mapping",
        "typing.MutableMapping",
        "typing.Sequence",
        "typing.MutableSequence",
        "typing.ByteString",
        "typing.Tuple",
        "typing.List",
        "typing.Deque",
        "typing.Set",
        "typing.FrozenSet",
        "typing.MappingView",
        "typing.KeysView",
        "typing.ItemsView",
        "typing.ValuesView",
        "typing.ContextManager",
        "typing.AsyncContextManager",
        "typing.Dict",
        "typing.DefaultDict",
        "typing.OrderedDict",
        "typing.Counter",
        "typing.ChainMap",
        "typing.Generator",
        "typing.AsyncGenerator",
        "typing.Type",
        "typing.Pattern",
        "typing.Match",
    )
)

CLASS_GETITEM_TEMPLATE = """
@classmethod
def __class_getitem__(cls, item):
    return cls
"""


def looks_like_typing_typevar_or_newtype(node):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname in TYPING_TYPEVARS
    if isinstance(func, nodes.Name):
        return func.name in TYPING_TYPEVARS
    return False


def infer_typing_typevar_or_newtype(node, context=None):
    """Infer a typing.TypeVar(...) or typing.NewType(...) call"""
    try:
        func = next(node.func.infer(context=context))
    except InferenceError as exc:
        raise UseInferenceDefault from exc

    if func.qname() not in TYPING_TYPEVARS_QUALIFIED:
        raise UseInferenceDefault
    if not node.args:
        raise UseInferenceDefault

    typename = node.args[0].as_string().strip("'")
    node = extract_node(TYPING_TYPE_TEMPLATE.format(typename))
    return node.infer(context=context)


def _looks_like_typing_subscript(node):
    """Try to figure out if a Subscript node *might* be a typing-related subscript"""
    if isinstance(node, nodes.Name):
        return node.name in TYPING_MEMBERS
    elif isinstance(node, nodes.Attribute):
        return node.attrname in TYPING_MEMBERS
    elif isinstance(node, nodes.Subscript):
        return _looks_like_typing_subscript(node.value)
    return False


def infer_typing_attr(
    node: nodes.Subscript, ctx: context.InferenceContext = None
) -> typing.Iterator[nodes.ClassDef]:
    """Infer a typing.X[...] subscript"""
    try:
        value = next(node.value.infer())
    except InferenceError as exc:
        raise UseInferenceDefault from exc

    if (
        not value.qname().startswith("typing.")
        or PY37
        and value.qname() in TYPING_ALIAS
    ):
        # If typing subscript belongs to an alias
        # (PY37+) handle it separately.
        raise UseInferenceDefault

    if (
        PY37
        and isinstance(value, nodes.ClassDef)
        and value.qname()
        in ("typing.Generic", "typing.Annotated", "typing_extensions.Annotated")
    ):
        # With PY37+ typing.Generic and typing.Annotated (PY39) are subscriptable
        # through __class_getitem__. Since astroid can't easily
        # infer the native methods, replace them for an easy inference tip
        func_to_add = astroid.extract_node(CLASS_GETITEM_TEMPLATE)
        value.locals["__class_getitem__"] = [func_to_add]
        if (
            isinstance(node.parent, nodes.ClassDef)
            and node in node.parent.bases
            and getattr(node.parent, "__cache", None)
        ):
            # node.parent.slots is evaluated and cached before the inference tip
            # is first applied. Remove the last result to allow a recalculation of slots
            cache = getattr(node.parent, "__cache")
            if cache.get(node.parent.slots) is not None:
                del cache[node.parent.slots]
        return iter([value])

    node = extract_node(TYPING_TYPE_TEMPLATE.format(value.qname().split(".")[-1]))
    return node.infer(context=ctx)


def _looks_like_typedDict(  # pylint: disable=invalid-name
    node: nodes.FunctionDef,
) -> bool:
    """Check if node is TypedDict FunctionDef."""
    return isinstance(node, nodes.FunctionDef) and node.name == "TypedDict"


def infer_typedDict(  # pylint: disable=invalid-name
    node: nodes.FunctionDef, ctx: context.InferenceContext = None
) -> typing.Iterator[nodes.ClassDef]:
    """Replace TypedDict FunctionDef with ClassDef."""
    class_def = nodes.ClassDef(
        name="TypedDict",
        lineno=node.lineno,
        col_offset=node.col_offset,
        parent=node.parent,
    )
    return iter([class_def])


def _looks_like_typing_alias(node: nodes.Call) -> bool:
    """
    Returns True if the node corresponds to a call to _alias function.
    For example :

    MutableSet = _alias(collections.abc.MutableSet, T)

    :param node: call node
    """
    return (
        isinstance(node, nodes.Call)
        and isinstance(node.func, nodes.Name)
        and node.func.name == "_alias"
        and (
            # _alias function works also for builtins object such as list and dict
            isinstance(node.args[0], nodes.Attribute)
            or isinstance(node.args[0], nodes.Name)
            and node.args[0].name != "type"
        )
    )


def _forbid_class_getitem_access(node: nodes.ClassDef) -> None:
    """
    Disable the access to __class_getitem__ method for the node in parameters
    """

    def full_raiser(origin_func, attr, *args, **kwargs):
        """
        Raises an AttributeInferenceError in case of access to __class_getitem__ method.
        Otherwise just call origin_func.
        """
        if attr == "__class_getitem__":
            raise AttributeInferenceError("__class_getitem__ access is not allowed")
        else:
            return origin_func(attr, *args, **kwargs)

    try:
        node.getattr("__class_getitem__")
        # If we are here, then we are sure to modify object that do have __class_getitem__ method (which origin is one the
        # protocol defined in collections module) whereas the typing module consider it should not
        # We do not want __class_getitem__ to be found in the classdef
        partial_raiser = partial(full_raiser, node.getattr)
        node.getattr = partial_raiser
    except AttributeInferenceError:
        pass


def infer_typing_alias(
    node: nodes.Call, ctx: context.InferenceContext = None
) -> typing.Iterator[nodes.ClassDef]:
    """
    Infers the call to _alias function
    Insert ClassDef, with same name as aliased class,
    in mro to simulate _GenericAlias.

    :param node: call node
    :param context: inference context
    """
    if (
        not isinstance(node.parent, nodes.Assign)
        or not len(node.parent.targets) == 1
        or not isinstance(node.parent.targets[0], nodes.AssignName)
    ):
        return None
    res = next(node.args[0].infer(context=ctx))
    assign_name = node.parent.targets[0]

    class_def = nodes.ClassDef(
        name=assign_name.name,
        lineno=assign_name.lineno,
        col_offset=assign_name.col_offset,
        parent=node.parent,
    )
    if res != astroid.Uninferable and isinstance(res, nodes.ClassDef):
        # Only add `res` as base if it's a `ClassDef`
        # This isn't the case for `typing.Pattern` and `typing.Match`
        class_def.postinit(bases=[res], body=[], decorators=None)

    maybe_type_var = node.args[1]
    if (
        not PY39
        and not (
            isinstance(maybe_type_var, node_classes.Tuple) and not maybe_type_var.elts
        )
        or PY39
        and isinstance(maybe_type_var, nodes.Const)
        and maybe_type_var.value > 0
    ):
        # If typing alias is subscriptable, add `__class_getitem__` to ClassDef
        func_to_add = astroid.extract_node(CLASS_GETITEM_TEMPLATE)
        class_def.locals["__class_getitem__"] = [func_to_add]
    else:
        # If not, make sure that `__class_getitem__` access is forbidden.
        # This is an issue in cases where the aliased class implements it,
        # but the typing alias isn't subscriptable. E.g., `typing.ByteString` for PY39+
        _forbid_class_getitem_access(class_def)
    return iter([class_def])


MANAGER.register_transform(
    nodes.Call,
    inference_tip(infer_typing_typevar_or_newtype),
    looks_like_typing_typevar_or_newtype,
)
MANAGER.register_transform(
    nodes.Subscript, inference_tip(infer_typing_attr), _looks_like_typing_subscript
)

if PY39:
    MANAGER.register_transform(
        nodes.FunctionDef, inference_tip(infer_typedDict), _looks_like_typedDict
    )

if PY37:
    MANAGER.register_transform(
        nodes.Call, inference_tip(infer_typing_alias), _looks_like_typing_alias
    )
