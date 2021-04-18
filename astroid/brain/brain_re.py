# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/LICENSE
import sys

import astroid
from astroid import MANAGER, context, inference_tip, nodes

PY36 = sys.version_info >= (3, 6)
PY37 = sys.version_info[:2] >= (3, 7)
PY39 = sys.version_info[:2] >= (3, 9)

if PY36:
    # Since Python 3.6 there is the RegexFlag enum
    # where every entry will be exposed via updating globals()

    def _re_transform():
        return astroid.parse(
            """
        import sre_compile
        ASCII = sre_compile.SRE_FLAG_ASCII
        IGNORECASE = sre_compile.SRE_FLAG_IGNORECASE
        LOCALE = sre_compile.SRE_FLAG_LOCALE
        UNICODE = sre_compile.SRE_FLAG_UNICODE
        MULTILINE = sre_compile.SRE_FLAG_MULTILINE
        DOTALL = sre_compile.SRE_FLAG_DOTALL
        VERBOSE = sre_compile.SRE_FLAG_VERBOSE
        A = ASCII
        I = IGNORECASE
        L = LOCALE
        U = UNICODE
        M = MULTILINE
        S = DOTALL
        X = VERBOSE
        TEMPLATE = sre_compile.SRE_FLAG_TEMPLATE
        T = TEMPLATE
        DEBUG = sre_compile.SRE_FLAG_DEBUG
        """
        )

    astroid.register_module_extender(astroid.MANAGER, "re", _re_transform)


CLASS_GETITEM_TEMPLATE = """
@classmethod
def __class_getitem__(cls, item):
    return cls
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
        and node.parent.targets[0].name in ("Pattern", "Match")
    )


def infer_pattern_match(node: nodes.Call, ctx: context.InferenceContext = None):
    """Infer re.Pattern and re.Match as classes. For PY39+ add `__class_getitem__`."""
    class_def = nodes.ClassDef(
        name=node.parent.targets[0].name,
        lineno=node.lineno,
        col_offset=node.col_offset,
        parent=node.parent,
    )
    if PY39:
        func_to_add = astroid.extract_node(CLASS_GETITEM_TEMPLATE)
        class_def.locals["__class_getitem__"] = [func_to_add]
    return iter([class_def])


if PY37:
    MANAGER.register_transform(
        nodes.Call, inference_tip(infer_pattern_match), _looks_like_pattern_or_match
    )
