# Copyright (c) 2016 LOGILAB S.A. (Paris, FRANCE)
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


from astroid import exceptions
from astroid.interpreter import runtimeabc
from astroid.interpreter import objects
from astroid.tree import treeabc
from astroid import util


@util.singledispatch
def can_assign(node, attrname):
    """Check if the given attribute can be assigned onto the given node.

    By default, everything is assignable.
    """
    return True


def _settable_property(func_node, attrname):
    expected_setter = "%s.setter" % (attrname, )
    if not func_node.decorators:
        return False

    for decorator in func_node.decorators.nodes:
        if decorator.as_string() == expected_setter:
            return True


@can_assign.register(runtimeabc.Instance)
def _instance_can_assign(node, attrname):
    try:
        slots = node.slots()
    except TypeError:
        pass
    else:
        if slots and attrname not in set(slot.value for slot in slots):
            return False

    # Check non settable property.
    try:
        names = node.getattr(attrname)
    except exceptions.AttributeInferenceError:
        # In what circumstances can this fail?
        return True

    if not all(isinstance(name, treeabc.FunctionDef) for name in names):
        return True

    if len(names) == 1 and objects.is_property(names[0]):
        # This should even emit a type checking error.
        return False
    elif all(objects.is_property(name) or _settable_property(name, attrname)
             for name in names):
        return True
    return False
