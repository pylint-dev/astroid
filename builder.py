# copyright 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
# copyright 2003-2010 Sylvain Thenault, all rights reserved.
# contact mailto:thenault@gmail.com
#
# This file is part of logilab-astng.
#
# logilab-astng is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# logilab-astng is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with logilab-astng. If not, see <http://www.gnu.org/licenses/>.
"""The ASTNGBuilder makes astng from living object and / or from compiler.ast

With python >= 2.5, the internal _ast module is used instead

The builder is not thread safe and can't be used to parse different sources
at the same time.
"""

__docformat__ = "restructuredtext en"

import sys
from os.path import splitext, basename, dirname, exists, abspath
from inspect import isfunction, ismethod, ismethoddescriptor, isclass, \
     isbuiltin
from inspect import isdatadescriptor

from logilab.common.modutils import modpath_from_file

from logilab.astng.exceptions import ASTNGBuildingException, InferenceError
from logilab.astng.raw_building import build_module, object_build_class, \
     object_build_function, object_build_datadescriptor, attach_dummy_node, \
     object_build_methoddescriptor, attach_const_node, attach_import_node
from logilab.astng.rebuilder import TreeRebuilder
from logilab.astng.manager import ASTNGManager
from logilab.astng.bases import YES, Instance

from _ast import PyCF_ONLY_AST
def parse(string):
    return compile(string, "<string>", 'exec', PyCF_ONLY_AST)

if sys.version_info >= (3, 0):
    from tokenize import detect_encoding

    def open_source_file(filename):
        byte_stream = open(filename, 'bU')
        encoding = detect_encoding(byte_stream.readline)[0]
        stream = open(filename, 'U', encoding=encoding)
        try:
            data = stream.read()
        except UnicodeError, uex: # wrong encodingg
            # detect_encoding returns utf-8 if no encoding specified
            msg = 'Wrong (%s) or no encoding specified' % encoding
            raise ASTNGBuildingException(msg)
        return stream, encoding, data

else:
    import re

    _ENCODING_RGX = re.compile("[^#]*#*.*coding[:=]\s*([^\s]+)")

    def _guess_encoding(string):
        """get encoding from a python file as string or return None if not found
        """
        # check for UTF-8 byte-order mark
        if string.startswith('\xef\xbb\xbf'):
            return 'UTF-8'
        for line in string.split('\n', 2)[:2]:
            # check for encoding declaration
            match = _ENCODING_RGX.match(line)
            if match is not None:
                return match.group(1)

    def open_source_file(filename):
        """get data for parsing a file"""
        stream = open(filename, 'U')
        data = stream.read()
        encoding = _guess_encoding(data)
        return stream, encoding, data

# ast NG builder ##############################################################

MANAGER = ASTNGManager()

class ASTNGBuilder:
    """provide astng building methods
    """
    rebuilder = TreeRebuilder()

    def __init__(self, manager=None):
        self._manager = manager or MANAGER
        self._module = None
        self._done = None
        self._dyn_modname_map = {'gtk': 'gtk._gtk'}

    def module_build(self, module, modname=None):
        """build an astng from a living module instance
        """
        node = None
        self._module = module
        path = getattr(module, '__file__', None)
        if path is not None:
            path_, ext = splitext(module.__file__)
            if ext in ('.py', '.pyc', '.pyo') and exists(path_ + '.py'):
                node = self.file_build(path_ + '.py', modname)
        if node is None:
            # this is a built-in module
            # get a partial representation by introspection
            node = self.inspect_build(module, modname=modname, path=path)
        return node

    def inspect_build(self, module, modname=None, path=None):
        """build astng from a living module (i.e. using inspect)
        this is used when there is no python source code available (either
        because it's a built-in module or because the .py is not available)
        """
        self._module = module
        if modname is None:
            modname = module.__name__
        node = build_module(modname, module.__doc__)
        node.file = node.path = path and abspath(path) or path
        if self._manager is not None:
            self._manager._cache[modname] = node
        node.package = hasattr(module, '__path__')
        self._done = {}
        self.object_build(node, module)
        return node

    def file_build(self, path, modname=None):
        """build astng from a source code file (i.e. from an ast)

        path is expected to be a python source file
        """
        try:
            stream, encoding, data = open_source_file(path)
        except IOError, exc:
            msg = 'Unable to load file %r (%s)' % (path, exc)
            raise ASTNGBuildingException(msg)
        except SyntaxError, exc: # py3k encoding specification error
            raise ASTNGBuildingException(exc)
        except LookupError, exc: # unknown encoding
            raise ASTNGBuildingException(exc)
        # get module name if necessary, *before modifying sys.path*
        if modname is None:
            try:
                modname = '.'.join(modpath_from_file(path))
            except ImportError:
                modname = splitext(basename(path))[0]
        # build astng representation
        try:
            sys.path.insert(0, dirname(path)) # XXX (syt) iirk
            node = self.string_build(data, modname, path)
        finally:
            sys.path.pop(0)
        node.file_encoding = encoding
        node.file_stream = stream
        return node

    def string_build(self, data, modname='', path=None):
        """build astng from source code string and return rebuilded astng"""
        module = self._data_build(data, modname, path)
        if self._manager is not None:
            self._manager._cache[module.name] = module
        # post tree building steps after we stored the module in the cache:
        for from_node in module._from_nodes:
            self.add_from_names_to_locals(from_node)
        # handle delayed assattr nodes
        for delayed in module._delayed_assattr:
            self.delayed_assattr(delayed)
        return module

    def _data_build(self, data, modname, path):
        """build tree node from data and add some informations"""
        # this method could be wrapped with a pickle/cache function
        node = parse(data + '\n')
        if path is not None:
            node_file = abspath(path)
        else:
            node_file = '<?>'
        if modname.endswith('.__init__'):
            modname = modname[:-9]
            package = True
        else:
            package = path and path.find('__init__.py') > -1 or False
        self.rebuilder.init()
        module = self.rebuilder.visit_module(node, modname, package)
        module.file = module.path = node_file
        module._from_nodes = self.rebuilder._from_nodes
        module._delayed_assattr = self.rebuilder._delayed_assattr
        return module

    def add_from_names_to_locals(self, node):
        """store imported names to the locals;
        resort the locals if coming from a delayed node
        """

        _key_func = lambda node: node.fromlineno
        def sort_locals(my_list):
            my_list.sort(key=_key_func)
        for (name, asname) in node.names:
            if name == '*':
                try:
                    imported = node.root().import_module(node.modname)
                except ASTNGBuildingException:
                    continue
                for name in imported.wildcard_import_names():
                    node.parent.set_local(name, node)
                    sort_locals(node.parent.scope().locals[name])
            else:
                node.parent.set_local(asname or name, node)
                sort_locals(node.parent.scope().locals[asname or name])

    def delayed_assattr(self, node):
        """visit a AssAttr node -> add name to locals, handle members
        definition
        """
        try:
            frame = node.frame()
            for infered in node.expr.infer():
                if infered is YES:
                    continue
                try:
                    if infered.__class__ is Instance:
                        infered = infered._proxied
                        iattrs = infered.instance_attrs
                    elif isinstance(infered, Instance):
                        # Const, Tuple, ... we may be wrong, may be not, but
                        # anyway we don't want to pollute builtin's namespace
                        continue
                    elif infered.is_function:
                        iattrs = infered.instance_attrs
                    else:
                        iattrs = infered.locals
                except AttributeError:
                    # XXX log error
                    #import traceback
                    #traceback.print_exc()
                    continue
                values = iattrs.setdefault(node.attrname, [])
                if node in values:
                    continue
                # get assign in __init__ first XXX useful ?
                if frame.name == '__init__' and values and not \
                       values[0].frame().name == '__init__':
                    values.insert(0, node)
                else:
                    values.append(node)
        except InferenceError:
            pass


    # astng from living objects ###############################################
    #
    # this is actually a really minimal representation, including only Module,
    # Function and Class nodes and some others as guessed

    def object_build(self, node, obj):
        """recursive method which create a partial ast from real objects
         (only function, class, and method are handled)
        """
        if obj in self._done:
            return self._done[obj]
        self._done[obj] = node
        for name in dir(obj):
            try:
                member = getattr(obj, name)
            except AttributeError:
                # damned ExtensionClass.Base, I know you're there !
                attach_dummy_node(node, name)
                continue
            if ismethod(member):
                member = member.im_func
            if isfunction(member):
                # verify this is not an imported function
                if member.func_code.co_filename != getattr(self._module, '__file__', None):
                    attach_dummy_node(node, name, member)
                    continue
                object_build_function(node, member, name)
            elif isbuiltin(member):
                # verify this is not an imported member
                if self._member_module(member) != self._module.__name__:
                    imported_member(node, member, name)
                    continue
                object_build_methoddescriptor(node, member, name)
            elif isclass(member):
                # verify this is not an imported class
                if self._member_module(member) != self._module.__name__:
                    imported_member(node, member, name)
                    continue
                if member in self._done:
                    class_node = self._done[member]
                    if not class_node in node.locals.get(name, ()):
                        node.add_local_node(class_node, name)
                else:
                    class_node = object_build_class(node, member, name)
                    # recursion
                    self.object_build(class_node, member)
                if name == '__class__' and class_node.parent is None:
                    class_node.parent = self._done[self._module]
            elif ismethoddescriptor(member):
                assert isinstance(member, object)
                object_build_methoddescriptor(node, member, name)
            elif isdatadescriptor(member):
                assert isinstance(member, object)
                object_build_datadescriptor(node, member, name)
            elif isinstance(member, (int, long, float, str, unicode)) or member is None:
                attach_const_node(node, name, member)
            else:
                # create an empty node so that the name is actually defined
                attach_dummy_node(node, name, member)

    def _member_module(self, member):
        modname = getattr(member, '__module__', None)
        return self._dyn_modname_map.get(modname, modname)


def imported_member(node, member, name):
    """consider a class/builtin member where __module__ != current module name

    check if it's sound valid and then add an import node, else use a dummy node
    """
    # /!\ some classes like ExtensionClass doesn't have a
    # __module__ attribute !
    member_module = getattr(member, '__module__', '__builtin__')
    try:
        getattr(sys.modules[member_module], name)
    except (KeyError, AttributeError):
        attach_dummy_node(node, name, member)
    else:
        attach_import_node(node, member_module, name)

