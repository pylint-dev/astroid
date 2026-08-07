# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Astroid hooks for the wave module."""

from __future__ import annotations

from astroid import context, nodes, util
from astroid.exceptions import InferenceError
from astroid.inference_tip import inference_tip
from astroid.manager import AstroidManager


def _looks_like_wave_open(node: nodes.Call) -> bool:
    """Check if the call is to ``wave.open``."""
    func = node.func
    return (
        isinstance(func, nodes.Attribute)
        and func.attrname == "open"
        and isinstance(func.expr, nodes.Name)
        and func.expr.name == "wave"
    )


def _infer_wave_open(
    node: nodes.Call, context: context.InferenceContext | None = None
) -> util.Generator[util.InferenceResult, None, None]:
    """Infer ``wave.open`` based on the mode argument.

    ``wave.open`` returns a :class:`wave.Wave_read` instance for modes
    ``'r'``/``'rb'`` and a :class:`wave.Wave_write` instance for modes
    ``'w'``/``'wb'``.
    """
    if not _looks_like_wave_open(node):
        raise util.UseInferenceDefault

    mode = None
    mode_arg = None
    if len(node.args) > 1:
        mode_arg = node.args[1]
    else:
        for keyword in node.keywords or []:
            if keyword.arg == "mode":
                mode_arg = keyword.value
                break
    if mode_arg is not None:
        modes: set[str] = set()
        try:
            for inferred in mode_arg.infer(context):
                if isinstance(inferred, nodes.Const) and isinstance(
                    inferred.value, str
                ):
                    modes.add(inferred.value)
        except (InferenceError, StopIteration):
            pass
        if modes and all(m in ("r", "rb") for m in modes):
            mode = "r"
        elif modes and all(m in ("w", "wb") for m in modes):
            mode = "w"

    try:
        wave_module = AstroidManager().ast_from_module_name("wave")
        read_class = next(wave_module.igetattr("Wave_read"))
        write_class = next(wave_module.igetattr("Wave_write"))
    except (InferenceError, StopIteration) as exc:
        raise util.UseInferenceDefault from exc

    if mode == "r":
        return iter([read_class.instantiate_class()])
    if mode == "w":
        return iter([write_class.instantiate_class()])
    # Unknown mode (or defaulting to the mode of a file-like object):
    # return both possibilities to avoid false positives.
    return iter([read_class.instantiate_class(), write_class.instantiate_class()])


def register(manager: AstroidManager) -> None:
    manager.register_transform(
        nodes.Call, inference_tip(_infer_wave_open), _looks_like_wave_open
    )
