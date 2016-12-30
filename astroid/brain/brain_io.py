# Copyright (c) 2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

'''Astroid brain hints for some of the _io C objects.'''

import astroid


BUFFERED = {'BufferedWriter', 'BufferedReader', 'BufferedRandom'}
TextIOWrapper = 'TextIOWrapper'
FileIO = 'FileIO'
BufferedWriter = 'BufferedWriter'
IOBase = '_IOBase'


def _generic_io_transform(node, name, cls):
    '''Transform the given name, by adding the given *class* as a member of the node.'''

    io_module = astroid.MANAGER.ast_from_module_name('_io')
    attribute_object = io_module[cls]
    instance = attribute_object.instantiate_class()
    node.locals[name] = [instance]


def _transform_text_io_wrapper(node):
    # This is not always correct, since it can vary with the type of the descriptor,
    # being stdout, stderr or stdin. But we cannot get access to the name of the
    # stream, which is why we are using the BufferedWriter class as a default
    # value
    return _generic_io_transform(node, name='buffer', cls=BufferedWriter)


def _transform_buffered(node):
    return _generic_io_transform(node, name='raw', cls=FileIO)


def _enter_returns_self(node):
    """
    Transform ClassDef nodes in such way, that empty __enter__ nodes returns
    `self`. Mandatory for correct inference of context manager protocol.
    TODO: implement whole known file protocol?
    (for less Uninferable results on method calls)
    """
    enter_funcdefs = [funcdef for funcdef in node.body
                      if isinstance(funcdef, astroid.FunctionDef)
                      and funcdef.name == "__enter__"]
    if not enter_funcdefs:
        return
    enter_funcdef = enter_funcdefs[0]
    if enter_funcdef.body:
        return
    code = """
    class Class(object):
        def __enter__(self):
            return self
    """
    fake_node = astroid.extract_node(code)
    enter_funcdef.args = fake_node.body[0].args
    enter_funcdef.body = fake_node.body[0].body


astroid.MANAGER.register_transform(astroid.ClassDef,
                                   _transform_buffered,
                                   lambda node: node.name in BUFFERED)
astroid.MANAGER.register_transform(astroid.ClassDef,
                                   _transform_text_io_wrapper,
                                   lambda node: node.name == TextIOWrapper)
astroid.MANAGER.register_transform(astroid.ClassDef,
                                   _enter_returns_self,
                                   lambda node: any(c.name == IOBase for c in node.ancestors()))
