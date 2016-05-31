# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""Astroid hooks for the Python standard library."""

# Namedtuple template strings
from collections import _class_template, _repr_template, _field_template
import functools
import sys
import textwrap

from astroid import (
    MANAGER, UseInferenceDefault, inference_tip)
from astroid import exceptions
from astroid import nodes
from astroid.builder import AstroidBuilder
from astroid import parse
from astroid import util

PY3K = sys.version_info > (3, 0)
PY33 = sys.version_info >= (3, 3)
PY34 = sys.version_info >= (3, 4)

def infer_first(node, context):
    if node is util.Uninferable:
        raise exceptions.InferenceError(
            'Could not infer an Uninferable node.',
            node=node, context=context)

    value = next(node.infer(context=context), None)
    if value in (util.Uninferable, None):
        raise UseInferenceDefault()
    else:
        return value


# namedtuple and Enum support

def _looks_like(node, name):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname == name
    if isinstance(func, nodes.Name):
        return func.name == name
    return False

_looks_like_namedtuple = functools.partial(_looks_like, name='namedtuple')
_looks_like_enum = functools.partial(_looks_like, name='Enum')


def infer_namedtuple_enum_fields(call_node, context):
    # node is a Call node, class name as first argument and generated class
    # attributes as second argument
    if len(call_node.args) != 2:
        # something weird here, go back to class implementation
        raise UseInferenceDefault()
    # namedtuple or enums list of attributes can be a list of strings or a
    # whitespace-separate string
    try:
        type_name = infer_first(call_node.args[0], context).value
        # The type might not be inferred properly in the case it is a string
        # formatting operation, such as '{...}'.format(...)
        type_name = type_name or "Uninferable"

        fields = infer_first(call_node.args[1], context)
        return type_name, fields
    except (AttributeError, exceptions.InferenceError):
        raise UseInferenceDefault()


def infer_namedtuple(namedtuple_call, context=None):
    """Specific inference function for namedtuple Call node"""

    type_name, fields = infer_namedtuple_enum_fields(namedtuple_call, context)
    if isinstance(fields, nodes.Const) and isinstance(fields.value, str):
        field_names = tuple(fields.value.replace(',', ' ').split())
    elif isinstance(fields, (nodes.Tuple, nodes.List)):
        field_names = tuple(infer_first(const, context).value
                            for const in fields.elts)
    else:
        raise UseInferenceDefault()

    if not field_names:
        raise UseInferenceDefault()

    class_definition = _class_template.format(
        typename = type_name,
        field_names = field_names,
        num_fields = len(field_names),
        arg_list = repr(field_names).replace("'", "")[1:-1],
        repr_fmt = ', '.join(_repr_template.format(name=name)
                             for name in field_names),
        field_defs = '\n'.join(_field_template.format(index=index, name=name)
                               for index, name in enumerate(field_names))
    )
    namedtuple_node = parse(class_definition).getattr(type_name)[0]
    init_template = '''def __init__(self, {args}):
{assignments}
    '''
    init_definition = init_template.format(
        args=', '.join(field_names),
        assignments='\n'.join((' ' * 4 + 'self.{f} = {f}').format(f=f) for f in field_names))

    init_node = parse(init_definition).getattr('__init__')[0]
    init_node.parent = namedtuple_node
    namedtuple_node.body.append(init_node)
    # This is an ugly hack to work around the normal process for
    # assigning to instance_attrs relying on inference and thus being
    # affected by instance_attrs already present.
    for assignment in init_node.body:
        namedtuple_node.instance_attrs[assignment.targets[0].attrname].append(assignment.targets[0])
    return iter([namedtuple_node])


def infer_enum(enum_call, context=None):
    """ Specific inference function for enum Call node. """
    type_name, fields = infer_namedtuple_enum_fields(enum_call, context)
    try:
         attributes = tuple(fields.value.replace(',', ' ').split())
    except AttributeError as exception:
        # Enums supports either iterator of (name, value) pairs
        # or mappings.
        # TODO: support only list, tuples and mappings.
        if hasattr(fields, 'items') and isinstance(fields.items, list):
            attributes = [infer_first(const[0], context).value
                          for const in fields.items
                          if isinstance(const[0], nodes.Const)]
        elif hasattr(fields, 'elts'):
            # Enums can support either ["a", "b", "c"]
            # or [("a", 1), ("b", 2), ...], but they can't
            # be mixed.
            if all(isinstance(const, nodes.Tuple)
                   for const in fields.elts):
                attributes = [infer_first(const.elts[0], context).value
                              for const in fields.elts
                              if isinstance(const, nodes.Tuple)]
            else:
                attributes = [infer_first(const, context).value
                              for const in fields.elts]
        else:
            util.reraise(exception)
        if not attributes:
            util.reraise(exception)
    
    template = textwrap.dedent('''
    """Mock module to hold enum classes"""
    class EnumMeta(object):
        """Mock Enum metaclass"""
    class EnumAttribute(object):
         def __init__(self,  name=''):
             self.name = name
             self.value = 0

    class {name}(EnumMeta):
        """Mock Enum class"""
        def __call__(self, node):
            return EnumAttribute()

        def __init__(self, {attributes}):
            """Fake __init__ for enums"""
    ''')
    code = template.format(name=type_name, attributes=', '.join(attributes))
    assignment_lines = [(' '*8 + 'self.{a} = EnumAttribute("{a}")'.format(a=a))
                        for a in attributes]
    code += '\n'.join(assignment_lines)
    module = AstroidBuilder(MANAGER).string_build(code)
    built_class = module.locals[type_name][0]
    return iter([built_class.instantiate_class()])


def infer_enum_class(enum_node):
    """ Specific inference for enums. """
    names = {'Enum', 'IntEnum', 'enum.Enum', 'enum.IntEnum'}
    for basename in enum_node.basenames:
        # TODO: doesn't handle subclasses yet. This implementation
        # is a hack to support enums.
        if basename not in names:
            continue
        if enum_node.root().name == 'enum':
            # Skip if the class is directly from enum module.
            break
        for local, values in enum_node.locals.items():
            if any(not isinstance(value, nodes.AssignName)
                   for value in values):
                continue

            stmt = values[0].statement()
            if isinstance(stmt.targets[0], nodes.Tuple):
                targets = stmt.targets[0].itered()
            else:
                targets = stmt.targets

            # new_targets = []
            for target in targets:
                # Replace all the assignments with our mocked class.
                classdef = textwrap.dedent('''
                class %(name)s(%(types)s):
                    @property
                    def value(self):
                        # Not the best return.
                        return None
                    @property
                    def name(self):
                        return %(name)r
                ''' % {'name': target.name, 'types': ', '.join(enum_node.basenames)})
                class_node = parse(classdef)[target.name]
                class_node.parent = target.parent
                for method in enum_node.mymethods():
                    class_node.body.append(method)
                    method.parent = class_node
                instance_node = nodes.InterpreterObject(name=local, object_=class_node.instantiate_class(), parent=enum_node.parent)
                # Replace the Assign node with the Enum instance
                enum_node.body[enum_node.body.index(target.parent)] = instance_node
        break
    return enum_node


MANAGER.register_transform(nodes.Call, inference_tip(infer_namedtuple),
                           _looks_like_namedtuple)
MANAGER.register_transform(nodes.Call, inference_tip(infer_enum),
                           _looks_like_enum)
MANAGER.register_transform(nodes.ClassDef, infer_enum_class)
