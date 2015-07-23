# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
"""astroid manager: avoid multiple astroid build of a same module when
possible by providing a class responsible to get astroid representation
from various source and using a cache of built modules)
"""
from __future__ import print_function

import collections
import imp
import os
import warnings
import zipimport

from astroid.exceptions import AstroidBuildingException
from astroid import modutils


def safe_repr(obj):
    try:
        return repr(obj)
    except Exception: # pylint: disable=broad-except
        return '???'


class AstroidManager(object):
    """the astroid manager, responsible to build astroid from files
     or modules.

    Use the Borg pattern.
    """

    name = 'astroid loader'
    brain = {}

    def __init__(self):
        self.__dict__ = AstroidManager.brain
        if not self.__dict__:
            # NOTE: cache entries are added by the [re]builder
            self.astroid_cache = {}
            self._mod_file_cache = {}
            self.transforms = collections.defaultdict(list)
            self._failed_import_hooks = []
            self.always_load_extensions = False
            self.optimize_ast = False
            self.extension_package_whitelist = set()

    def ast_from_file(self, filepath, modname=None, fallback=True, source=False):
        """given a module name, return the astroid object"""
        try:
            filepath = modutils.get_source_file(filepath, include_no_ext=True)
            source = True
        except modutils.NoSourceFile:
            pass
        if modname is None:
            try:
                modname = '.'.join(modutils.modpath_from_file(filepath))
            except ImportError:
                modname = filepath
        if modname in self.astroid_cache and self.astroid_cache[modname].file == filepath:
            return self.astroid_cache[modname]
        if source:
            from astroid.builder import AstroidBuilder
            return AstroidBuilder(self).file_build(filepath, modname)
        elif fallback and modname:
            return self.ast_from_module_name(modname)
        raise AstroidBuildingException('unable to get astroid for file %s' %
                                       filepath)

    def _build_stub_module(self, modname):
        from astroid.builder import AstroidBuilder
        return AstroidBuilder(self).string_build('', modname)

    def _can_load_extension(self, modname):
        if self.always_load_extensions:
            return True
        if modutils.is_standard_module(modname):
            return True
        parts = modname.split('.')
        return any(
            '.'.join(parts[:x]) in self.extension_package_whitelist
            for x in range(1, len(parts) + 1))

    def ast_from_module_name(self, modname, context_file=None):
        """given a module name, return the astroid object"""
        if modname in self.astroid_cache:
            return self.astroid_cache[modname]
        if modname == '__main__':
            return self._build_stub_module(modname)
        old_cwd = os.getcwd()
        if context_file:
            os.chdir(os.path.dirname(context_file))
        try:
            filepath, mp_type = self.file_from_module_name(modname, context_file)
            if mp_type == modutils.PY_ZIPMODULE:
                module = self.zip_import_data(filepath)
                if module is not None:
                    return module
            elif mp_type in (imp.C_BUILTIN, imp.C_EXTENSION):
                if mp_type == imp.C_EXTENSION and not self._can_load_extension(modname):
                    return self._build_stub_module(modname)
                try:
                    module = modutils.load_module_from_name(modname)
                except Exception as ex:
                    msg = 'Unable to load module %s (%s)' % (modname, ex)
                    raise AstroidBuildingException(msg)
                return self.ast_from_module(module, modname)
            elif mp_type == imp.PY_COMPILED:
                raise AstroidBuildingException("Unable to load compiled module %s" % (modname,))
            if filepath is None:
                raise AstroidBuildingException("Unable to load module %s" % (modname,))
            return self.ast_from_file(filepath, modname, fallback=False)
        except AstroidBuildingException as e:
            for hook in self._failed_import_hooks:
                try:
                    return hook(modname)
                except AstroidBuildingException:
                    pass
            raise e
        finally:
            os.chdir(old_cwd)

    def zip_import_data(self, filepath):
        if zipimport is None:
            return None
        from astroid.builder import AstroidBuilder
        builder = AstroidBuilder(self)
        for ext in ('.zip', '.egg'):
            try:
                eggpath, resource = filepath.rsplit(ext + os.path.sep, 1)
            except ValueError:
                continue
            try:
                importer = zipimport.zipimporter(eggpath + ext)
                zmodname = resource.replace(os.path.sep, '.')
                if importer.is_package(resource):
                    zmodname = zmodname + '.__init__'
                module = builder.string_build(importer.get_source(resource),
                                              zmodname, filepath)
                return module
            except Exception: # pylint: disable=broad-except
                continue
        return None

    def file_from_module_name(self, modname, contextfile):
        try:
            value = self._mod_file_cache[(modname, contextfile)]
        except KeyError:
            try:
                value = modutils.file_info_from_modpath(
                    modname.split('.'), context_file=contextfile)
            except ImportError as ex:
                msg = 'Unable to load module %s (%s)' % (modname, ex)
                value = AstroidBuildingException(msg)
            self._mod_file_cache[(modname, contextfile)] = value
        if isinstance(value, AstroidBuildingException):
            raise value
        return value

    def ast_from_module(self, module, modname=None):
        """given an imported module, return the astroid object"""
        modname = modname or module.__name__
        if modname in self.astroid_cache:
            return self.astroid_cache[modname]
        try:
            # some builtin modules don't have __file__ attribute
            filepath = module.__file__
            if modutils.is_python_source(filepath):
                return self.ast_from_file(filepath, modname)
        except AttributeError:
            pass
        from astroid.builder import AstroidBuilder
        return AstroidBuilder(self).module_build(module, modname)

    def ast_from_class(self, klass, modname=None):
        """get astroid for the given class"""
        if modname is None:
            try:
                modname = klass.__module__
            except AttributeError:
                raise AstroidBuildingException(
                    'Unable to get module for class %s' % safe_repr(klass))
        modastroid = self.ast_from_module_name(modname)
        return modastroid.getattr(klass.__name__)[0] # XXX

    def infer_ast_from_something(self, obj, context=None):
        """infer astroid for the given class"""
        if hasattr(obj, '__class__') and not isinstance(obj, type):
            klass = obj.__class__
        else:
            klass = obj
        try:
            modname = klass.__module__
        except AttributeError:
            raise AstroidBuildingException(
                'Unable to get module for %s' % safe_repr(klass))
        except Exception as ex:
            raise AstroidBuildingException(
                'Unexpected error while retrieving module for %s: %s'
                % (safe_repr(klass), ex))
        try:
            name = klass.__name__
        except AttributeError:
            raise AstroidBuildingException(
                'Unable to get name for %s' % safe_repr(klass))
        except Exception as ex:
            raise AstroidBuildingException(
                'Unexpected error while retrieving name for %s: %s'
                % (safe_repr(klass), ex))
        # take care, on living object __module__ is regularly wrong :(
        modastroid = self.ast_from_module_name(modname)
        if klass is obj:
            for  infered in modastroid.igetattr(name, context):
                yield infered
        else:
            for infered in modastroid.igetattr(name, context):
                yield infered.instanciate_class()

    def register_transform(self, node_class, transform, predicate=None):
        """Register `transform(node)` function to be applied on the given
        Astroid's `node_class` if `predicate` is None or returns true
        when called with the node as argument.

        The transform function may return a value which is then used to
        substitute the original node in the tree.
        """
        self.transforms[node_class].append((transform, predicate))

    def unregister_transform(self, node_class, transform, predicate=None):
        """Unregister the given transform."""
        self.transforms[node_class].remove((transform, predicate))

    def register_failed_import_hook(self, hook):
        """Registers a hook to resolve imports that cannot be found otherwise.

        `hook` must be a function that accepts a single argument `modname` which
        contains the name of the module or package that could not be imported.
        If `hook` can resolve the import, must return a node of type `astroid.Module`,
        otherwise, it must raise `AstroidBuildingException`.
        """
        self._failed_import_hooks.append(hook)

    def transform(self, node):
        """Call matching transforms for the given node if any and return the
        transformed node.
        """
        cls = node.__class__
        if cls not in self.transforms:
            # no transform registered for this class of node
            return node

        transforms = self.transforms[cls]
        orig_node = node  # copy the reference
        for transform_func, predicate in transforms:
            if predicate is None or predicate(node):
                ret = transform_func(node)
                # if the transformation function returns something, it's
                # expected to be a replacement for the node
                if ret is not None:
                    if node is not orig_node:
                        # node has already be modified by some previous
                        # transformation, warn about it
                        warnings.warn('node %s substituted multiple times' % node)
                    node = ret
        return node

    def cache_module(self, module):
        """Cache a module if no module with the same name is known yet."""
        self.astroid_cache.setdefault(module.name, module)

    def clear_cache(self, astroid_builtin=None):
        # XXX clear transforms
        self.astroid_cache.clear()
        # force bootstrap again, else we may ends up with cache inconsistency
        # between the manager and CONST_PROXY, making
        # unittest_lookup.LookupTC.test_builtin_lookup fail depending on the
        # test order
        import astroid.raw_building
        astroid.raw_building._astroid_bootstrapping(
            astroid_builtin=astroid_builtin)
