# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Regression coverage for compiled regular-expression result models."""

from types import SimpleNamespace

import pytest

import astroid
from astroid import bases, nodes, util
from astroid.brain import brain_re
from astroid.builder import extract_node


def infer(expression, prefix="import re\n"):
    return list(extract_node(f"{prefix}{expression} #@").infer())


def types(values):
    return {value.pytype() for value in values}


def match_infer(expression, literal="'x'"):
    return infer(
        f"    match.{expression}",
        f"import re\nmatch = re.compile({literal}).match({literal})\nif match:\n",
    )


@pytest.mark.parametrize("method", ["match", "search", "fullmatch"])
@pytest.mark.parametrize("literal", ["'x'", "b'x'"])
def test_pattern_matching_is_optional_match(method, literal):
    assert types(infer(f"re.compile({literal}).{method}({literal})")) == {
        "re.Match",
        "builtins.NoneType",
    }


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("findall('x')", "builtins.list"),
        ("split('x')", "builtins.list"),
        ("finditer('x')", "builtins.generator"),
        ("flags", "builtins.int"),
        ("groups", "builtins.int"),
        ("groupindex", "builtins.dict"),
    ],
)
def test_pattern_result_families(expression, expected):
    values = infer(f"re.compile('x').{expression}")
    assert types(values) == {expected}
    if expected != "builtins.generator":
        assert all(value.bool_value() is util.Uninferable for value in values)


@pytest.mark.parametrize(
    "literal, expected", [("'x'", "builtins.str"), ("b'x'", "builtins.bytes")]
)
def test_text_result_families(literal, expected):
    assert types(infer(f"re.compile({literal}).sub({literal}, {literal})")) == {
        expected
    }
    assert types(match_infer("group()", literal)) == {expected}
    assert types(match_infer(f"expand({literal})", literal)) == {expected}
    assert types(match_infer("group(1)", literal)) == {expected, "builtins.NoneType"}
    pair = infer(f"re.compile({literal}).subn({literal}, {literal})")[0]
    assert isinstance(pair, nodes.Tuple)
    assert len(pair.elts) == 2
    assert types(pair.elts[0].infer()) == {expected}
    assert types(pair.elts[1].infer()) == {"builtins.int"}


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("start()", {"builtins.int"}),
        ("end()", {"builtins.int"}),
        ("groups()", {"builtins.tuple"}),
        ("groups(default='fallback')", {"builtins.tuple"}),
        ("groupdict()", {"builtins.dict"}),
        ("groupdict(default='fallback')", {"builtins.dict"}),
        ("pos", {"builtins.int"}),
        ("endpos", {"builtins.int"}),
        ("lastindex", {"builtins.int", "builtins.NoneType"}),
        ("lastgroup", {"builtins.str", "builtins.NoneType"}),
        ("re", {"re.Pattern"}),
        ("string", {"builtins.str"}),
        ("regs", {"builtins.tuple"}),
    ],
)
def test_match_result_families(expression, expected):
    assert types(match_infer(expression)) == expected


def test_known_tuple_shapes_do_not_invent_values():
    span = match_infer("span()")[0]
    assert isinstance(span, nodes.Tuple)
    assert len(span.elts) == 2
    assert all(types(elt.infer()) == {"builtins.int"} for elt in span.elts)
    groups = match_infer("group(1, 'name')")[0]
    assert isinstance(groups, nodes.Tuple)
    assert len(groups.elts) == 2
    assert all(
        types(elt.infer()) == {"builtins.str", "builtins.NoneType"}
        for elt in groups.elts
    )


@pytest.mark.parametrize(
    "expression,prefix",
    [
        ("rx.compile('x')", "import re as rx\n"),
        ("compile_regex('x')", "from re import compile as compile_regex\n"),
        ("alias('x')", "import re\nalias = re.compile\n"),
        ("re.compile(pattern='x', flags=0)", "import re\n"),
        ("re.compile(re.compile('x'))", "import re\n"),
    ],
)
def test_compile_aliases_and_keyword_pattern(expression, prefix):
    assert types(infer(expression, prefix)) == {"re.Pattern"}


@pytest.mark.parametrize(
    "prefix",
    [
        "class re:\n    @staticmethod\n    def compile(pattern):\n        return 42\n",
        "def compile(pattern):\n    return 42\nre = type('Other', (), {'compile': compile})\n",
    ],
)
def test_unrelated_re_compile_is_not_hijacked(prefix):
    values = infer("re.compile('x')", prefix)
    assert len(values) == 1
    assert isinstance(values[0], nodes.Const)
    assert values[0].value == 42


def test_unknown_member_is_not_hidden():
    with pytest.raises(astroid.InferenceError):
        infer("re.compile('x').not_a_regex_method")


def test_pattern_metadata_and_match_identity():
    assert [value.value for value in infer("re.compile(b'x').pattern")] == [b"x"]
    result = match_infer("re")[0]
    assert isinstance(result, bases.Instance)
    assert result.qname() == "re.Pattern"
    assert types(list(result.getattr("pattern")[0].infer())) == {"builtins.str"}


@pytest.mark.parametrize("expression", ["findall('x')", "split('x')", "groupindex"])
def test_unknown_container_contents_do_not_imply_length(expression):
    value = infer(f"re.compile('x').{expression}")[0]
    assert not isinstance(value, (nodes.List, nodes.Dict, nodes.Tuple))
    assert value.bool_value() is util.Uninferable


@pytest.mark.parametrize(
    "expression",
    [
        "re.compile('x').match(b'x')",
        "re.compile(b'x').match('x')",
        "re.compile('x').match(42)",
        "re.compile('x').match()",
        "re.compile('x').match('x', 0, 1, 2)",
        "re.compile('x').match('x', string='x')",
        "re.compile('x').match('x', unknown=1)",
        "re.compile('x').match(string=missing)",
        "re.compile('x').match('x', pos='bad')",
        "re.compile('x').sub(b'x', 'x')",
        "re.compile(b'x').sub('x', b'x')",
        "re.compile('x').sub(42, 'x')",
        "re.compile()",
        "re.compile('x', 0, 1)",
        "re.compile('x', pattern='x')",
        "re.compile(42)",
        "re.compile(missing)",
        "re.compile('x', flags='bad')",
        "re.compile('x', flags=missing)",
        "re.compile(re.compile('x'), flags=2)",
        "re.compile(*missing)",
        "re.compile(**missing)",
        "re.compile('x', flags=0, **{'flags': 2})",
        "re.compile('x')[0]",
    ],
)
def test_invalid_or_unknown_calls_do_not_invent_results(expression):
    try:
        values = infer(expression)
    except astroid.InferenceError:
        return
    assert all(value is util.Uninferable for value in values)


def test_scanner_preserves_string_and_owner():
    values = infer("re.compile(b'x').scanner(b'xyz').match()")
    match = next(value for value in values if isinstance(value, bases.Instance))
    assert match.getattr("string")[0].value == b"xyz"
    assert match.getattr("re")[0].getattr("pattern")[0].value == b"x"
    assert types(infer("re.compile('x').scanner('x').search()")) == {
        "re.Match",
        "builtins.NoneType",
    }


def test_scanner_is_not_generic():
    with pytest.raises(astroid.InferenceError):
        infer("re.compile('x').scanner('x').__class_getitem__(str)")


@pytest.mark.parametrize(
    "key, expected",
    [("0", {"builtins.str"}), ("'name'", {"builtins.str", "builtins.NoneType"})],
)
def test_match_subscript(key, expected):
    values = infer(
        f"    match[{key}]",
        "import re\nmatch = re.compile('x').match('x')\nif match:\n",
    )
    assert types(values) == expected


def test_instances_and_bound_aliases_do_not_share_metadata():
    prefix = """
import re
p1 = re.compile('a')
p2 = re.compile(b'b')
lookup = p1.match
m1 = lookup('aa')
m2 = p2.match(b'bb')
if m1:
"""
    assert types(infer("    m1.group()", prefix)) == {"builtins.str"}
    assert [value.value for value in infer("    m1.re.pattern", prefix)] == ["a"]
    assert types(infer("p2.sub(b'x', b'b')", prefix + "    pass\n")) == {
        "builtins.bytes"
    }
    assert [value.value for value in infer("p2.pattern", prefix + "    pass\n")] == [
        b"b"
    ]


def test_unknown_lengths_are_not_fabricated():
    for expression in (
        "len(re.compile('x').findall('x'))",
        "len(re.compile('x').groupindex)",
    ):
        value = util.safe_infer(extract_node(f"import re\n{expression} #@"))
        assert not isinstance(value, nodes.Const)


def test_valid_offsets_and_callable_replacement():
    assert types(infer("re.compile('x').match('xx', pos=0, endpos=1)")) == {
        "re.Match",
        "builtins.NoneType",
    }
    assert types(infer("re.compile('x').split('xx', maxsplit=1)")) == {"builtins.list"}
    assert types(infer("re.compile('x').sub(lambda match: 'x', 'xx', count=1)")) == {
        "builtins.str"
    }


@pytest.mark.parametrize("key", ["1.5", "missing"])
def test_invalid_group_keys_do_not_invent_text(key):
    with pytest.raises(astroid.InferenceError):
        match_infer(f"group({key})")


def test_standard_compile_import_and_unrelated_import():
    assert types(infer("compile('x')", "from re import compile\n")) == {"re.Pattern"}
    node = extract_node("from re import match as other\nother('x', 'x') #@")
    assert not brain_re._looks_like_re_compile(node)


def test_match_cannot_be_compiled_as_a_pattern():
    try:
        values = infer(
            "    re.compile(match)",
            "import re\nmatch = re.compile('x').match('x')\nif match:\n",
        )
    except astroid.InferenceError:
        return
    assert all(value is util.Uninferable for value in values)


def test_copy_and_iterator_keep_owner():
    pattern = infer("re.compile(b'x')")[0]
    copy_method = next(pattern.igetattr("__copy__"))
    assert list(copy_method.infer_call_result(None)) == [pattern]
    assert types(infer("re.compile('x').__deepcopy__({})")) == {"re.Pattern"}
    assert types(match_infer("__copy__()")) == {"re.Match"}
    iterator = infer("re.compile(b'x').finditer(b'xyz')")[0]
    match = next(iterator.infer_yield_types())
    assert match.getattr("string")[0].value == b"xyz"
    assert match.getattr("re")[0].getattr("pattern")[0].value == b"x"
    inherited = next(pattern.igetattr("__str__"))
    assert not isinstance(inherited, brain_re._RegexMethod)
    subscription = next(pattern.igetattr("__class_getitem__"))
    assert not isinstance(subscription, brain_re._RegexMethod)


def test_prefixmatch_version_guard(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(brain_re, "PY315_PLUS", True)
        astroid.MANAGER.clear_cache()
        assert types(infer("re.compile('x').prefixmatch('x')")) == {
            "re.Match",
            "builtins.NoneType",
        }
    astroid.MANAGER.clear_cache()


@pytest.mark.parametrize("exception", [AttributeError, IndexError, StopIteration])
def test_pattern_lookup_failure_remains_uninferable(monkeypatch, exception):
    node = extract_node("import re\nre.compile('x') #@")
    list(node.func.infer())

    def fail_lookup(_name):
        raise exception("forced unavailable re.Pattern lookup")

    manager = SimpleNamespace(ast_from_module_name=fail_lookup)
    monkeypatch.setattr(brain_re, "AstroidManager", lambda: manager)
    assert list(brain_re.infer_re_compile(node)) == [util.Uninferable]


def test_non_class_pattern_remains_uninferable(monkeypatch):
    node = extract_node("import re\nre.compile('x') #@")
    list(node.func.infer())
    module = SimpleNamespace(getattr=lambda _name: [nodes.Const(42)])
    manager = SimpleNamespace(ast_from_module_name=lambda _name: module)
    monkeypatch.setattr(brain_re, "AstroidManager", lambda: manager)
    assert list(brain_re.infer_re_compile(node)) == [util.Uninferable]


def test_typed_unknown_values_can_be_composed():
    prefix = "import re\np = re.compile('x')\n"
    assert types(infer("p.match('x', pos=p.groups)", prefix)) == {
        "re.Match",
        "builtins.NoneType",
    }
    assert types(infer("re.compile('x', flags=p.flags)", prefix)) == {"re.Pattern"}
    assert infer("re.compile(p, flags=p.flags)", prefix) == [util.Uninferable]
    assert types(infer("re.compile(p, flags=0)", prefix)) == {"re.Pattern"}
    assert types(match_infer("re.search(match.string, pos=match.end())")) == {
        "re.Match",
        "builtins.NoneType",
    }
    assert types(match_infer("group(match.end())")) == {
        "builtins.str",
        "builtins.NoneType",
    }
    values = infer(
        "    re.compile(match.group())",
        "import re\nmatch = re.compile('x').match('x')\nif match:\n",
    )
    assert types(values) == {"re.Pattern"}


@pytest.mark.parametrize(
    "code, expected",
    [
        ("from re import compile as alias\nalias('x') #@", True),
        ("import re\nalias: object = re.compile\nalias('x') #@", True),
        (
            "import re\nalias = re.compile\ndef wrapper():\n    alias('x') #@",
            True,
        ),
        (
            "import re\ndef outer():\n    alias = re.compile\n"
            "    def inner():\n        alias('x') #@",
            True,
        ),
        ("def unrelated(pattern):\n    return 42\nunrelated('x') #@", False),
        ("from builtins import int as alias\nalias('x') #@", False),
        ("alias = 42\nalias('x') #@", False),
    ],
)
def test_compile_candidate_detection_does_not_resolve_names(
    monkeypatch, code, expected
):
    node = extract_node(code)

    def unexpected_lookup(_name):
        pytest.fail("The parse-time candidate predicate must not resolve names")

    monkeypatch.setattr(node.func, "lookup", unexpected_lookup)
    assert brain_re._looks_like_re_compile(node) is expected


def test_shadowed_outer_compile_alias_uses_normal_inference():
    values = infer(
        "wrapper()",
        "import re\nalias = re.compile\ndef wrapper():\n"
        "    alias = lambda pattern: 42\n    return alias('x')\n",
    )
    assert [value.value for value in values] == [42]


@pytest.mark.parametrize(
    "prefix, expression",
    [
        (
            "import re\nalias = re.compile\ndef wrapper():\n"
            "    global alias\n    return alias('x')\n",
            "wrapper()",
        ),
        (
            "import re\ndef outer():\n    alias = re.compile\n"
            "    def inner():\n        nonlocal alias\n        return alias('x')\n"
            "    return inner()\n",
            "outer()",
        ),
        (
            "import re\ndef outer():\n    alias = re.compile\n"
            "    def inner():\n        return alias('x')\n    return inner()\n",
            "outer()",
        ),
        ("import re\nalias: object = re.compile\n", "alias('x')"),
        (
            "import re\nalias = re.compile\nclass Wrapper:\n"
            "    alias = lambda pattern: 42\n    def method(self):\n"
            "        return alias('x')\n",
            "Wrapper().method()",
        ),
    ],
)
def test_compile_aliases_in_enclosing_scopes(prefix, expression):
    assert types(infer(expression, prefix)) == {"re.Pattern"}
