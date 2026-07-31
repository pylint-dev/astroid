# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from collections.abc import Iterator

from astroid import bases, context, nodes, util
from astroid.brain.helpers import register_module_extender
from astroid.builder import _extract_single_node, parse
from astroid.const import PY311_PLUS
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager


def _re_transform() -> nodes.Module:
    # The RegexFlag enum exposes all its entries by updating globals()
    # In 3.6-3.10 all flags come from sre_compile
    # On 3.11+ all flags come from re._compiler
    if PY311_PLUS:
        import_compiler = "import re._compiler as _compiler"
    else:
        import_compiler = "import sre_compile as _compiler"
    return parse(f"""
    {import_compiler}
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

def match(self, string, pos=0, endpos=-1):
    pass

def fullmatch(self, string, pos=0, endpos=-1):
    pass

def search(self, string, pos=0, endpos=-1):
    pass

def sub(self, repl, string, count=0):
    pass

def subn(self, repl, string, count=0):
    pass

def split(self, string, maxsplit=0):
    pass

def findall(self, string, pos=0, endpos=-1):
    pass

def finditer(self, string, pos=0, endpos=-1):
    pass

def scanner(self, string, pos=0, endpos=-1):
    pass
"""


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


def infer_pattern_match(node: nodes.Call, ctx: context.InferenceContext | None = None):
    """Infer re.Pattern and re.Match as classes.

    For PY39+ add `__class_getitem__` and the regular expression methods.
    """
    class_def = nodes.ClassDef(
        name=node.parent.targets[0].name,
        lineno=node.lineno,
        col_offset=node.col_offset,
        parent=node.parent,
        end_lineno=node.end_lineno,
        end_col_offset=node.end_col_offset,
    )
    template_module = parse(CLASS_GETITEM_TEMPLATE)
    for func in template_module.body:
        class_def.locals[func.name] = [func]
    return iter([class_def])


def _looks_like_re_compile(node: nodes.Call) -> bool:
    """Check for a call to re.compile."""
    if len(node.args) == 0:
        return False
    func = node.func
    if isinstance(func, nodes.Attribute):
        return (
            func.attrname == "compile"
            and isinstance(func.expr, nodes.Name)
            and func.expr.name == "re"
        )
    if isinstance(func, nodes.Name):
        return func.name == "compile"
    return False


def infer_re_compile(
    node: nodes.Call, ctx: context.InferenceContext | None = None
) -> Iterator[bases.Instance]:
    """Infer the result of re.compile as an instance of re.Pattern."""
    from astroid.manager import AstroidManager  # pylint: disable=import-outside-toplevel

    re_module = AstroidManager().ast_from_module_name("re")
    try:
        pattern = next(re_module.getattr("Pattern")[0].infer())
    except (AttributeError, IndexError, StopIteration):
        return iter([util.Uninferable])
    if not isinstance(pattern, nodes.ClassDef):
        return iter([util.Uninferable])
    return iter([pattern.instantiate_class()])


def register(manager: AstroidManager) -> None:
    register_module_extender(manager, "re", _re_transform)
    manager.register_transform(
        nodes.Call, inference_tip(infer_pattern_match), _looks_like_pattern_or_match
    )
    manager.register_transform(
        nodes.Call, inference_tip(infer_re_compile), _looks_like_re_compile
    )
