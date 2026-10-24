# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import sys
from collections.abc import Iterator

from astroid import arguments, bases, nodes, util
from astroid.brain.helpers import register_module_extender
from astroid.builder import _extract_single_node, parse
from astroid.const import PY315_PLUS
from astroid.context import CallContext, InferenceContext, copy_context
from astroid.exceptions import InferenceError, UseInferenceDefault
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager
from astroid.typing import InferenceResult


def _re_transform() -> nodes.Module:
    # The RegexFlag enum exposes all its entries by updating globals()
    # All flags come from re._compiler
    return parse("""
    import re._compiler as _compiler
    NOFLAG = 0
    ASCII = _compiler.SRE_FLAG_ASCII
    IGNORECASE = _compiler.SRE_FLAG_IGNORECASE
    LOCALE = _compiler.SRE_FLAG_LOCALE
    UNICODE = _compiler.SRE_FLAG_UNICODE
    MULTILINE = _compiler.SRE_FLAG_MULTILINE
    DOTALL = _compiler.SRE_FLAG_DOTALL
    VERBOSE = _compiler.SRE_FLAG_VERBOSE
    TEMPLATE = _compiler.SRE_FLAG_TEMPLATE
    DEBUG = _compiler.SRE_FLAG_DEBUG
    A = ASCII
    I = IGNORECASE
    L = LOCALE
    U = UNICODE
    M = MULTILINE
    S = DOTALL
    X = VERBOSE
    T = TEMPLATE
    """)


CLASS_GETITEM_TEMPLATE = """
@classmethod
def __class_getitem__(cls, item):
    return cls
"""

_METHODS = {
    "Pattern": {
        "match": f"string, pos=0, endpos={sys.maxsize}",
        "search": f"string, pos=0, endpos={sys.maxsize}",
        "fullmatch": f"string, pos=0, endpos={sys.maxsize}",
        "findall": f"string, pos=0, endpos={sys.maxsize}",
        "finditer": f"string, pos=0, endpos={sys.maxsize}",
        "split": "string, maxsplit=0",
        "sub": "repl, string, count=0",
        "subn": "repl, string, count=0",
        "scanner": f"string, pos=0, endpos={sys.maxsize}",
        "__copy__": "",
        "__deepcopy__": "memo",
    },
    "Match": {
        "group": "*groups",
        "__getitem__": "key, /",
        "groups": "default=None",
        "groupdict": "default=None",
        "expand": "template",
        "start": "group=0, /",
        "end": "group=0, /",
        "span": "group=0, /",
        "__copy__": "",
        "__deepcopy__": "memo",
    },
    "SRE_Scanner": {"match": "", "search": ""},
}


class _UnknownValue(bases.Instance):
    """A known result type without an invented value, size or truth value."""

    def bool_value(self, context=None):
        return util.Uninferable


def _typed(name: str) -> _UnknownValue:
    return _UnknownValue(AstroidManager().builtins_module[name])


def _is_integer(value) -> bool:
    return value is not None and value.pytype() in {"builtins.int", "builtins.bool"}


def _bind_call(call, function):
    """Validate the modeled signature before manufacturing a result type."""
    parameters = function.args.posonlyargs + function.args.args
    if function.type == "method":
        parameters = parameters[1:]
    names = [parameter.name for parameter in parameters]
    kwargs = call.keyword_arguments
    positional = call.positional_arguments
    if call.has_invalid_arguments() or call.has_invalid_keywords():
        raise InferenceError
    if not function.args.vararg and len(positional) > len(names):
        raise InferenceError
    allowed_keywords = {argument.name for argument in function.args.args} - {"self"}
    if set(kwargs) - allowed_keywords or set(names[: len(positional)]).intersection(
        kwargs
    ):
        raise InferenceError
    bound = dict(zip(names, positional))
    bound.update(kwargs)
    required = names[: len(names) - len(function.args.defaults)]
    if set(required) - bound.keys():
        raise InferenceError
    return bound


def _model_class(name: str) -> nodes.ClassDef:
    signatures = _METHODS[name].copy()
    if PY315_PLUS and name == "Pattern":
        signatures["prefixmatch"] = signatures["match"]
    methods = "\n".join(
        f"    def {method}(self{', ' if signature else ''}{signature}):\n"
        "        raise NotImplementedError\n"
        for method, signature in signatures.items()
    )
    result = parse(f"class {name}:\n{methods}", module_name="re")[name]
    if name in {"Pattern", "Match"}:
        item = _extract_single_node(CLASS_GETITEM_TEMPLATE)
        item.parent = result
        result.locals["__class_getitem__"] = [item]
    return result


def _result_value(values, parent):
    result = nodes.Unknown(parent=parent)
    result._explicit_inference = lambda node, context: iter(values)
    return result


def _result_tuple(values: list[list[InferenceResult]], parent) -> nodes.Tuple:
    result = nodes.Tuple(parent=parent)
    result.postinit([_result_value(alternatives, result) for alternatives in values])
    return result


class _RegexInstance(bases.Instance):
    """Per-result regex metadata; never modify a shared class's locals."""

    def __init__(self, proxied, text_types, source, pattern=None):
        super().__init__(proxied)
        self.text_types = text_types
        self.pattern_instance = pattern
        self.source_values = source
        if proxied.name == "Pattern":
            self.regex_attributes = {
                "pattern": self.source_values,
                "flags": [_typed("int")],
                "groups": [_typed("int")],
                "groupindex": [_typed("dict")],
            }
        elif proxied.name == "Match":
            self.regex_attributes = {
                "string": self.source_values,
                "re": [pattern],
                "pos": [_typed("int")],
                "endpos": [_typed("int")],
                "lastindex": [_typed("int"), nodes.Const(None)],
                "lastgroup": [_typed("str"), nodes.Const(None)],
                "regs": [_typed("tuple")],
            }
        else:
            self.regex_attributes = {}

    def text_values(self):
        return [_typed(name) for name in self.text_types]

    def getattr(self, name, context=None, lookupclass=True):
        if name in self.regex_attributes:
            return self.regex_attributes[name]
        return super().getattr(name, context=context, lookupclass=lookupclass)

    def _wrap_attr(self, attrs, context=None):
        for attr in super()._wrap_attr(attrs, context):
            if (
                isinstance(attr, bases.BoundMethod)
                and attr.name in self._proxied.locals
                and attr.name != "__class_getitem__"
            ):
                yield _RegexMethod(attr._proxied, self)
            else:
                yield attr

    def getitem(self, index, context=None):
        if self._proxied.name != "Match":
            return super().getitem(index, context)
        new_context = copy_context(context)
        new_context.callcontext = CallContext([index])
        method = next(self.igetattr("__getitem__", context=new_context))
        return _result_value(
            list(method.infer_call_result(self, new_context)), self._proxied
        )


class _MatchIterator(bases.Generator):
    def __init__(self, parent, match):
        super().__init__(parent)
        self.match = match

    def infer_yield_types(self):
        yield self.match


class _RegexMethod(bases.BoundMethod):
    def infer_call_result(self, caller, context=None):
        bound = self.bound
        call_context = (
            context.callcontext if context and context.callcontext else CallContext([])
        )
        call = arguments.CallSite(call_context, context=context)
        bound_args = _bind_call(call, self._proxied)
        name = self.name
        text = bound.text_values()
        source_values = bound.source_values
        accepted = {f"builtins.{family}" for family in bound.text_types}
        if "bytes" in bound.text_types:
            accepted.update({"builtins.bytearray", "builtins.memoryview"})
        for argument in ("string", "template"):
            if argument in bound_args:
                value = util.safe_infer(bound_args[argument], context=context)
                value_type = value.pytype() if value is not None else None
                if value_type not in accepted:
                    raise InferenceError(node=caller, context=context)
                source_values = [value]
        for argument in ("pos", "endpos", "maxsplit", "count"):
            if argument in bound_args:
                value = util.safe_infer(bound_args[argument], context=context)
                if not _is_integer(value):
                    raise InferenceError(node=caller, context=context)
        if "repl" in bound_args:
            replacement = util.safe_infer(bound_args["repl"], context=context)
            if replacement is None or (
                replacement.pytype() not in accepted and not replacement.callable()
            ):
                raise InferenceError(node=caller, context=context)
        if name in {"__copy__", "__deepcopy__"}:
            yield bound
        elif name in {
            "match",
            "search",
            "fullmatch",
            "prefixmatch",
            "finditer",
            "scanner",
        }:
            pattern = (
                bound if bound._proxied.name == "Pattern" else bound.pattern_instance
            )
            match = _RegexInstance(
                _model_class("Match"), bound.text_types, source_values, pattern
            )
            if name == "finditer":
                yield _MatchIterator(bound._proxied.locals[name][0], match)
            elif name == "scanner":
                scanner_class = _model_class("SRE_Scanner")
                scanner_class.parent.name = "_sre"
                yield _RegexInstance(
                    scanner_class, bound.text_types, source_values, pattern
                )
            else:
                yield match
                yield nodes.Const(None)
        elif name in {"sub", "expand"}:
            yield from text
        elif name == "subn":
            yield _result_tuple([text, [_typed("int")]], bound._proxied)
        elif name in {"start", "end"}:
            yield _typed("int")
        elif name == "span":
            yield _result_tuple([[_typed("int")], [_typed("int")]], bound._proxied)
        elif name in {"findall", "split", "groups", "groupdict"}:
            yield _typed(
                {
                    "findall": "list",
                    "split": "list",
                    "groups": "tuple",
                    "groupdict": "dict",
                }[name]
            )
        else:
            if call.positional_arguments:
                keys = [
                    util.safe_infer(argument, context=context)
                    for argument in call.positional_arguments
                ]
                if any(
                    key is None
                    or key.pytype()
                    not in {"builtins.int", "builtins.bool", "builtins.str"}
                    for key in keys
                ):
                    raise InferenceError(node=caller, context=context)
                if any(
                    not isinstance(key, nodes.Const) or key.value != 0 for key in keys
                ):
                    text += [nodes.Const(None)]
            if len(call.positional_arguments) > 1:
                yield _result_tuple(
                    [text] * len(call.positional_arguments), bound._proxied
                )
            else:
                yield from text


def _looks_like_pattern_or_match(node: nodes.Call) -> bool:
    """Check for re.Pattern or re.Match call in stdlib.

    Match these patterns from stdlib/re.py
    ```py
    Pattern = type(...)
    Match = type(...)
    ```
    """
    return (
        node.root().name == "re"
        and isinstance(node.func, nodes.Name)
        and node.func.name == "type"
        and isinstance(node.parent, nodes.Assign)
        and len(node.parent.targets) == 1
        and isinstance(node.parent.targets[0], nodes.AssignName)
        and node.parent.targets[0].name in {"Pattern", "Match"}
    )


def infer_pattern_match(node: nodes.Call, ctx: InferenceContext | None = None):
    """Infer re.Pattern and re.Match as classes.

    For PY39+ add `__class_getitem__`.
    """
    class_def = _model_class(node.parent.targets[0].name)
    class_def.parent = node.parent
    return iter([class_def])


def _looks_like_re_compile(node: nodes.Call) -> bool:
    """Check for a call to re.compile (or compile() inside the re module)."""
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname == "compile"
    if not isinstance(func, nodes.Name):
        return False
    if func.name == "compile":
        return True
    for definition in func.lookup(func.name)[1]:
        if isinstance(definition, nodes.ImportFrom) and definition.modname == "re":
            if ("compile", func.name) in definition.names:
                return True
        if isinstance(definition, nodes.AssignName) and isinstance(
            definition.parent, (nodes.Assign, nodes.AnnAssign)
        ):
            value = definition.parent.value
            if isinstance(value, nodes.Attribute) and value.attrname == "compile":
                return True
    return False


def infer_re_compile(
    node: nodes.Call, ctx: InferenceContext | None = None
) -> Iterator[InferenceResult]:
    """Infer Pattern results without following re.compile's type-dependent fast path."""
    func = util.safe_infer(node.func, context=ctx)
    if not isinstance(func, nodes.FunctionDef) or func.qname() != "re.compile":
        raise UseInferenceDefault
    call = arguments.CallSite.from_call(node, context=ctx)
    try:
        bound_args = _bind_call(call, func)
    except InferenceError as exc:
        raise UseInferenceDefault from exc
    argument = call.keyword_arguments.get("pattern")
    if call.positional_arguments:
        argument = call.positional_arguments[0]
    if "flags" in bound_args:
        flags = util.safe_infer(bound_args["flags"], context=ctx)
        if not _is_integer(flags):
            raise UseInferenceDefault
    value = util.safe_infer(argument, context=ctx)
    if isinstance(value, _RegexInstance) and value._proxied.name == "Pattern":
        if "flags" in bound_args and (
            not isinstance(flags, nodes.Const) or flags.value
        ):
            return iter([util.Uninferable])
        return iter([value])
    value_type = value.pytype() if value is not None else None
    if value_type not in {"builtins.str", "builtins.bytes"}:
        raise UseInferenceDefault
    text_types = (value_type.removeprefix("builtins."),)
    try:
        re_module = AstroidManager().ast_from_module_name("re")
        pattern = next(re_module.getattr("Pattern")[0].infer())
    except (AttributeError, IndexError, StopIteration):
        return iter([util.Uninferable])
    if not isinstance(pattern, nodes.ClassDef):
        return iter([util.Uninferable])
    return iter([_RegexInstance(pattern, text_types, [value])])


def register(manager: AstroidManager) -> None:
    register_module_extender(manager, "re", _re_transform)
    manager.register_transform(
        nodes.Call, inference_tip(infer_pattern_match), _looks_like_pattern_or_match
    )
    manager.register_transform(
        nodes.Call, inference_tip(infer_re_compile), _looks_like_re_compile
    )
