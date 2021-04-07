# Copyright (c) 2017-2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 David Euresti <github@euresti.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>
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


def infer_typing_attr(node, context=None):
    """Infer a typing.X[...] subscript"""
    try:
        value = next(node.value.infer())
    except InferenceError as exc:
        raise UseInferenceDefault from exc

    if not value.qname().startswith("typing."):
        raise UseInferenceDefault

    node = extract_node(TYPING_TYPE_TEMPLATE.format(value.qname().split(".")[-1]))
    return node.infer(context=context)


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


CLASS_GETITEM_TEMPLATE = """
@classmethod
def __class_getitem__(cls, item):
    return cls
"""


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

    if not isinstance(node, nodes.ClassDef):
        raise TypeError("The parameter type should be ClassDef")
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
) -> typing.Optional[node_classes.NodeNG]:
    """
    Infers the call to _alias function

    :param node: call node
    :param context: inference context
    """
    res = next(node.args[0].infer(context=ctx))

    if res != astroid.Uninferable and isinstance(res, nodes.ClassDef):
        if not PY39:
            # Here the node is a typing object which is an alias toward
            # the corresponding object of collection.abc module.
            # Before python3.9 there is no subscript allowed for any of the collections.abc objects.
            # The subscript ability is given through the typing._GenericAlias class
            # which is the metaclass of the typing object but not the metaclass of the inferred
            # collections.abc object.
            # Thus we fake subscript ability of the collections.abc object
            # by mocking the existence of a __class_getitem__ method.
            # We can not add `__getitem__` method in the metaclass of the object because
            # the metaclass is shared by subscriptable and not subscriptable object
            maybe_type_var = node.args[1]
            if not (
                isinstance(maybe_type_var, node_classes.Tuple)
                and not maybe_type_var.elts
            ):
                # The typing object is subscriptable if the second argument of the _alias function
                # is a TypeVar or a tuple of TypeVar. We could check the type of the second argument but
                # it appears that in the typing module the second argument is only TypeVar or a tuple of TypeVar or empty tuple.
                # This last value means the type is not Generic and thus cannot be subscriptable
                func_to_add = astroid.extract_node(CLASS_GETITEM_TEMPLATE)
                res.locals["__class_getitem__"] = [func_to_add]
            else:
                # If we are here, then we are sure to modify object that do have __class_getitem__ method (which origin is one the
                # protocol defined in collections module) whereas the typing module consider it should not
                # We do not want __class_getitem__ to be found in the classdef
                _forbid_class_getitem_access(res)
        else:
            # Within python3.9 discrepencies exist between some collections.abc containers that are subscriptable whereas
            # corresponding containers in the typing module are not! This is the case at least for ByteString.
            # It is far more to complex and dangerous to try to remove __class_getitem__ method from all the ancestors of the
            # current class. Instead we raise an AttributeInferenceError if we try to access it.
            maybe_type_var = node.args[1]
            if isinstance(maybe_type_var, nodes.Const) and maybe_type_var.value == 0:
                # Starting with Python39 the _alias function is in fact instantiation of _SpecialGenericAlias class.
                # Thus the type is not Generic if the second argument of the call is equal to zero
                _forbid_class_getitem_access(res)
        return iter([res])
    return iter([astroid.Uninferable])


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
