# Copyright (c) 2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

'''Astroid brain hints for some of the _io C objects.'''

import astroid
from astroid import decorators
from astroid import util
from astroid.tree import treeabc


BUFFERED = {'BufferedWriter', 'BufferedReader'}
TextIOWrapper = 'TextIOWrapper'
FileIO = 'FileIO'
BufferedWriter = 'BufferedWriter'


def _parametrized_lazy_interpreter_object(cls):
    '''Get an InterpreterObject which delays its object until accessed

    The class can be used when we are not able to access objects from
    the _io module during transformation time.
    '''

    @util.register_implementation(treeabc.InterpreterObject)
    class LazyInterpreterObject(astroid.InterpreterObject):

        @decorators.cachedproperty
        def _io_module(self):
             return astroid.MANAGER.ast_from_module_name('_io')

        @decorators.cachedproperty
        def object(self):
             attribute_object = self._io_module[cls]
             return attribute_object.instantiate_class()

    return LazyInterpreterObject


def _generic_io_transform(node, name, cls):
    '''Transform the given name, by adding the given *class* as a member of the node.'''

    module = astroid.MANAGER.ast_from_module_name('io')
    interpreter_object_cls = _parametrized_lazy_interpreter_object(
        cls=cls)

    # TODO: for some reason, this works only if it is inserted as the
    # first value, please check why.
    node.body.insert(0, interpreter_object_cls(name=name, parent=module))


def _transform_text_io_wrapper(node):
    # This is not always correct, since it can vary with the type of the descriptor,
    # being stdout, stderr or stdin. But we cannot get access to the name of the
    # stream, which is why we are using the BufferedWriter class as a default
    # value
    return _generic_io_transform(node, name='buffer', cls=BufferedWriter)


def _transform_buffered(node):
    return _generic_io_transform(node, name='raw', cls=FileIO)


astroid.MANAGER.register_transform(astroid.ClassDef,
                                   _transform_buffered,
                                   lambda node: node.name in BUFFERED)
astroid.MANAGER.register_transform(astroid.ClassDef,
                                   _transform_text_io_wrapper,
                                   lambda node: node.name == TextIOWrapper)
