# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Functional tests: python files whose comments say what astroid must find.

Each ``.py`` file under ``tests/functional`` is parsed by astroid. A comment
at the end of a line is about the statement on that line (for an expression
statement, the expression). It is a path from that node, then what the path
leads to::

    Cat().speak()  # inferred: Const('meow')
    x = foo(1, 2)  # value.args[0].inferred: Const(1)  # value.func.name: 'foo'
    class Kitten(Cat): ...  # mro: kitten.Kitten, kitten.Cat, builtins.object

A step of the path is an attribute (``value``), an index (``args[0]``) or a
call with plain arguments (``lookup('x')``). ``inferred`` is a step too: the
path goes on for every inferred result, and the results are separated by
``|``, sorted: the order of inference is not checked. Used first on the assignment of one
name, it infers that name.

A node is written ``Type(value)``, a list ``[a, b]``, anything else as
Python would print it. A container holding more than constants is written
with its elements, ``Tuple(Name(apple), Const(1))``: one comment says it all.
Some last steps have their own, shorter, answer:

- ``inferred-type`` and ``inferred-value``: half of ``inferred``
- ``mro``, ``ancestors``, ``metaclass``, ``slots``: qualified names
- ``locals``, ``instance_attrs``: the names, sorted
- ``position``: ``line:column-end_line:end_column``
- ``as_string``, ``args``, ``argnames``, ``bool_value``, ``doc_node``
- ``getattr(color)``, ``igetattr(color)``: where an attribute is defined,
  and what is inferred for it

An error reads as its name (``InferenceError``). To check a part of a line
that no path reaches, wrap it in ``__(...)``, like for
``astroid.extract_node``.

A comment can be about another line, like in pylint: ``# +1: inferred: ...``
is about the next line, ``# -1:`` about the line above. Checks that do not fit
at the end of their line go above it, one per line.

To add a check, write the path with nothing after the colon and run
``pytest --remaster``: the answer is filled in, for you to review.

Like in the functional tests of pylint, what is expected can depend on the
interpreter:

- on one line, with a condition before the path:
  ``# <3.14: inferred: Const(1)  # >=3.14: inferred: Const(2)``
- for a whole file, with a ``.rc`` file next to it holding a
  ``[testoptions]`` section: ``min_pyver``, ``max_pyver``, ``requires``,
  ``except_implementations`` and ``exclude_platforms``.
"""

from __future__ import annotations

import ast
import configparser
import enum
import platform
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pytest_remaster import CaseData, GoldenMaster, InlineLine, discover_test_files

from astroid import bases, nodes, parse, util
from astroid.builder import _extract_expressions, _find_statement_by_line
from astroid.exceptions import AstroidError, InferenceError
from astroid.typing import InferenceResult

CASES_DIR = Path(__file__).parent / "functional"


def _type(inferred: InferenceResult) -> str:
    if isinstance(inferred, util.UninferableBase):
        return "Uninferable"
    return type(inferred).__name__


def _value(inferred: InferenceResult) -> str:
    if isinstance(inferred, util.UninferableBase):
        return ""
    if isinstance(inferred, nodes.Const):
        return repr(inferred.value)
    if isinstance(inferred, nodes.Dict):
        if all(_plain(key) and _plain(item) for key, item in inferred.items):
            return str(inferred.as_string())
        return ", ".join(f"{_show(key)}: {_show(item)}" for key, item in inferred.items)
    if isinstance(inferred, nodes.BaseContainer):
        if all(_plain(element) for element in inferred.elts):
            return str(inferred.as_string())
        return ", ".join(_show(element) for element in inferred.elts)
    if isinstance(inferred, nodes.EvaluatedObject):
        return _show(inferred.value)
    if isinstance(inferred, (nodes.LocalsDictNodeNG, bases.Proxy, bases.UnboundMethod)):
        return str(inferred.qname())
    return ""


def _plain(node: object) -> bool:
    """Whether *node* is a constant, or a container of constants only."""
    if isinstance(node, nodes.Const):
        return True
    if isinstance(node, nodes.Dict):
        return all(_plain(key) and _plain(item) for key, item in node.items)
    return isinstance(node, nodes.BaseContainer) and all(map(_plain, node.elts))


def _both(inferred: InferenceResult) -> str:
    value = _value(inferred)
    return f"{_type(inferred)}({value})" if value else _type(inferred)


def _value_or_type(inferred: InferenceResult) -> str:
    return _value(inferred) or _type(inferred)


def _inferable(node: nodes.NodeNG) -> nodes.NodeNG:
    """``apple = 1  # inferred: Const(1)`` is about the name being assigned."""
    if isinstance(node, nodes.Assign) and len(node.targets) == 1:
        target = node.targets[0]
    elif isinstance(node, nodes.AnnAssign):
        target = node.target
    else:
        return node
    return target if isinstance(target, nodes.AssignName) else node


def _qnames(found) -> str:
    return ", ".join(str(node.qname()) for node in found) or "-"


def _mro(inferred) -> str:
    return _qnames(inferred.mro())


def _ancestors(inferred) -> str:
    return _qnames(inferred.ancestors())


def _metaclass(inferred) -> str:
    metaclass = inferred.metaclass()
    return "None" if metaclass is None else str(metaclass.qname())


def _slots(inferred) -> str:
    slots = inferred.slots()
    return "None" if slots is None else ", ".join(slot.value for slot in slots) or "-"


def _keys(attribute: str):
    return lambda inferred: ", ".join(sorted(getattr(inferred, attribute))) or "-"


def _bool_value(inferred) -> str:
    value = inferred.bool_value()
    return "Uninferable" if isinstance(value, util.UninferableBase) else str(value)


def _doc_node(inferred) -> str:
    return "None" if inferred.doc_node is None else repr(inferred.doc_node.value)


def _found(node: InferenceResult) -> str:
    """Describe a node found by a lookup, with its name when it has one."""
    described = _both(node)
    name = getattr(node, "name", None)
    return f"{described}({name})" if "(" not in described and name else described


def _getattr(answerer, name: str) -> str:
    # Sorted: the order of what ``getattr`` returns depends on what astroid
    # analysed before in the same process.
    return ", ".join(sorted(_found(node) for node in answerer.getattr(name))) or "-"


def _igetattr(answerer, name: str) -> str:
    found = sorted(_both(inferred) for inferred in answerer.igetattr(name))
    return " | ".join(found) or "-"


def _args(answerer) -> str:
    args = answerer.args
    if isinstance(args, nodes.Arguments):
        return args.as_string() or "-"
    return ", ".join(arg.as_string() for arg in args) or "-"


def _ask(question, answerer, *arguments: str) -> str:
    """Ask *question* to one node or inferred result.

    An API it does not have reads ``-``; an error reads as its name
    (``InconsistentMroError``).
    """
    if isinstance(answerer, util.UninferableBase):
        return "Uninferable"
    try:
        return str(question(answerer, *arguments))
    except (AstroidError, NotImplementedError, TypeError) as exc:
        return type(exc).__name__
    except AttributeError:
        return "-"


def _as_string(node: nodes.NodeNG) -> str:
    return node.as_string().replace("\\", "\\\\").replace("\n", "\\n")


def _position(node: nodes.NodeNG) -> str:
    return f"{node.lineno}:{node.col_offset}-{node.end_lineno}:{node.end_col_offset}"


# Last steps of a path with their own way of writing the answer.
QUESTIONS = {
    "mro": _mro,
    "ancestors": _ancestors,
    "metaclass": _metaclass,
    "slots": _slots,
    "locals": _keys("locals"),
    "instance_attrs": _keys("instance_attrs"),
    "bool_value": _bool_value,
    "doc_node": _doc_node,
    "as_string": _as_string,
    "position": _position,
    "args": _args,
    "argnames": lambda answerer: ", ".join(answerer.argnames()) or "-",
}
# The same, taking the name of an attribute: ``getattr(color)``.
LOOKUPS = {"getattr": _getattr, "igetattr": _igetattr}

_STEP = r"[A-Za-z_]\w*(?:-(?:type|value))?(?:\([^()#]*\)|\[[^\]\[#]*\])*"
# What the key of a comment looks like: a path of attributes, indexes and calls.
# Comments for other tools (``# type: ignore``) are not expectations.
KEY_PATTERN = (
    r"(?!(?:type|pylint|noqa|fmt|mypy|pyright|ruff|isort|pragma)\b)"
    rf"{_STEP}(?:\.{_STEP})*"
)


def _show(found: object) -> str:
    """Describe whatever a path leads to."""
    if isinstance(found, util.UninferableBase):
        return "Uninferable"
    if found is None or isinstance(found, (str, bytes, int, float, complex)):
        return repr(found)
    if isinstance(found, enum.Enum):
        return found.name
    if isinstance(found, (nodes.NodeNG, bases.Proxy)):
        described = _both(found)
        if "(" in described or not isinstance(found, nodes.NodeNG):
            return described
        text = found.as_string()
        return (
            f"{described}({text})"
            if "\n" not in text and len(text) <= 60
            else described
        )
    if isinstance(found, dict):
        return "{" + ", ".join(sorted(map(str, found))) + "}"
    if isinstance(found, (set, frozenset)):
        return "{" + ", ".join(sorted(_show(item) for item in found)) + "}"
    if isinstance(found, (list, tuple, Iterator)):
        return "[" + ", ".join(_show(item) for item in found) + "]"
    assert not callable(found), f"{found!r} is a method: call it, with ()"
    return type(found).__name__


class _Failed(str):
    """The name of the error a step of a path ended with."""

    __slots__ = ()


def _literal(argument: ast.expr) -> object:
    if isinstance(argument, ast.Name):
        return argument.id  # a bare word is text: getattr(color)
    if isinstance(argument, ast.Slice):
        bounds = (argument.lower, argument.upper, argument.step)
        return slice(*(None if b is None else ast.literal_eval(b) for b in bounds))
    return ast.literal_eval(argument)


def _steps(key: str) -> list[tuple[str, Any]]:
    """Split ``value.args[0].inferred`` in attribute, index and call steps."""

    def walk(expression: ast.expr) -> list[tuple[str, Any]]:
        if isinstance(expression, ast.Name):
            return [("attr", expression.id)]
        if isinstance(expression, ast.Attribute):
            return [*walk(expression.value), ("attr", expression.attr)]
        if isinstance(expression, ast.Subscript):
            return [*walk(expression.value), ("index", _literal(expression.slice))]
        if isinstance(expression, ast.Call) and not expression.keywords:
            arguments = [_literal(argument) for argument in expression.args]
            return [*walk(expression.func), ("call", arguments)]
        raise ValueError(f"cannot read the comment key {key!r}")

    return walk(ast.parse(key.replace("-", "_"), mode="eval").body)


def _step(item: Any, kind: str, value: Any) -> Any:
    try:
        if kind == "attr":
            return getattr(item, value)
        if kind == "index":
            return item[value]
        return item(*value)
    except (
        AstroidError,
        AttributeError,
        IndexError,
        KeyError,
        NotImplementedError,
        StopIteration,
        TypeError,
    ) as exc:
        return _Failed(type(exc).__name__)


def _infer(item: Any, first: bool) -> list[Any]:
    results: list[Any] = []
    try:
        for inferred in (_inferable(item) if first else item).infer():
            results.append(inferred)
    except InferenceError:
        results.append(_Failed("InferenceError"))
    except AttributeError:
        results.append(_Failed("AttributeError"))
    return results


def _infers(name: object) -> bool:
    """Whether the method called *name* yields inferred results."""
    return str(name).lstrip("_").startswith(("infer", "igetattr"))


def _drain(results: Iterator[Any]) -> list[Any]:
    drained: list[Any] = []
    try:
        for result in results:
            drained.append(result)
    except AstroidError as exc:
        drained.append(_Failed(type(exc).__name__))
    return drained


def describe(node: nodes.NodeNG, key: str) -> str:
    """Follow the path *key* from *node* and describe where it leads."""
    steps = _steps(key)
    render: Any = _show
    question, arguments = None, ()
    last = steps[-1]
    if last == ("attr", "inferred_type"):
        steps[-1], render = ("attr", "inferred"), _type
    elif last == ("attr", "inferred_value"):
        steps[-1] = ("attr", "inferred")
        render = _value_or_type
    elif last == ("attr", "inferred"):
        render = _both
    elif last[0] == "attr" and last[1] in QUESTIONS:
        question = QUESTIONS[steps.pop()[1]]
    elif last == ("call", []) and len(steps) > 1 and steps[-2][1] in QUESTIONS:
        question = QUESTIONS[steps[-2][1]]  # mro() reads like mro
        del steps[-2:]
    elif last[0] == "call" and len(steps) > 1 and steps[-2][1] in LOOKUPS:
        arguments = tuple(str(argument) for argument in last[1]) or ("",)
        question = LOOKUPS[steps[-2][1]]
        del steps[-2:]

    found, several, ordered = [node], False, True
    for index, (kind, value) in enumerate(steps):
        reached: list[Any] = []
        for item in found:
            if isinstance(item, _Failed):
                reached.append(item)
            elif (kind, value) == ("attr", "inferred"):
                several, ordered = True, False
                reached.extend(_infer(item, first=index == 0))
            elif isinstance(result := _step(item, kind, value), Iterator):
                # igetattr(), infer_call_result()...: the path goes on for each result
                several = True
                ordered = ordered and not _infers(steps[index - 1][1])
                reached.extend(_drain(result))
            else:
                reached.append(result)
        found = reached

    def answer(item: Any) -> str:
        if isinstance(item, _Failed):
            return str(item)
        return _ask(question, item, *arguments) if question else render(item)

    answers = [answer(item) for item in found]
    if not several:
        return answers[0]
    # The order astroid infers in is not part of what is checked.
    return " | ".join(answers if ordered else sorted(answers))


def node_on_line(
    module: nodes.Module, wrapped: dict[int, list[nodes.NodeNG]], line: InlineLine
) -> nodes.NodeNG:
    """Return the node the comment of *line* is about."""
    if line.lineno in wrapped:
        (node,) = wrapped[line.lineno]  # one __() per line
        return node
    statement = _find_statement_by_line(module, line.lineno)
    assert statement is not None, f"{line.path}:{line.lineno}: no statement here"
    return statement.value if isinstance(statement, nodes.Expr) else statement


def load(path: Path) -> tuple[nodes.Module, dict[int, list[nodes.NodeNG]]]:
    module = parse(path.read_text(encoding="utf-8"), module_name=path.stem)
    wrapped: dict[int, list[nodes.NodeNG]] = {}
    for node in _extract_expressions(module):
        wrapped.setdefault(node.lineno, []).append(node)
    return module, wrapped


CASES = [
    case for case in discover_test_files(CASES_DIR, "*.py") if case.id != "conftest.py"
]


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(digit) for digit in text.split("."))


def _names(text: str) -> list[str]:
    return [name.strip() for name in text.split(",") if name.strip()]


def skip_unless_supported(path: Path) -> None:
    """Skip the test when the ``.rc`` file of *path* rules out this interpreter."""
    parser = configparser.ConfigParser()
    parser.add_section("testoptions")
    parser.read(path.with_suffix(".rc"))
    options = dict(parser.items("testoptions"))
    known = {
        "min_pyver",
        "max_pyver",
        "requires",
        "except_implementations",
        "exclude_platforms",
    }
    assert options.keys() <= known, f"[testoptions] can only contain {known}"
    if sys.version_info < _version(
        options.get("min_pyver", "2.5")
    ) or sys.version_info > _version(options.get("max_pyver", "4.0")):
        pytest.skip("Test cannot run with this Python version.")
    missing = []
    for requirement in _names(options.get("requires", "")):
        try:
            __import__(requirement)
        except ImportError:
            missing.append(requirement)
    if missing:
        pytest.skip(f"Requires {','.join(missing)} to be present.")
    if platform.python_implementation() in _names(
        options.get("except_implementations", "")
    ):
        pytest.skip(f"Test cannot run with {platform.python_implementation()}.")
    if sys.platform.lower() in _names(options.get("exclude_platforms", "")):
        pytest.skip(f"Test cannot run on platform {sys.platform!r}")


@pytest.mark.parametrize("case", CASES)
def test_functional(case: CaseData, golden_master: GoldenMaster) -> None:
    skip_unless_supported(case.input)
    module, wrapped = load(case.input)
    golden_master.check_inline(
        case.input,
        describe,
        key_pattern=KEY_PATTERN,
        runner=lambda line: node_on_line(module, wrapped, line),
    )
