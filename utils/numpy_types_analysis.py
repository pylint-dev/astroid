#-*- encoding=utf-8 -*-
# Copyright (c) 2018 Guillaume Peillex <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER
"""
This module is used to determine common api between numpy core numerictypes
"""
import inspect


def get_numpy_core_numerictypes():
    """
    Returns the list of all classes defined inside numpy.core.numerictypes

    :return: all classes defined inside numpy.core.numerictypes
    :rtype: [(class_name, class_obj),...]
    """
    import numpy.core.numerictypes as nt
    return inspect.getmembers(nt, inspect.isclass)


def get_type_alias(members):
    """
    Returns the list of classes defined in members that are just an alias
    over another class

    :param members: input classes
    :type members: [(class_name, class_obj),...]
    :return: classes defined in members that are just an alias over another class
    :rtype: [(class_name, class_obj),...]
    """
    type_alias = []
    for t_name, class_obj in members:
        # The trick here is to build an instance of the class to be able
        # to get the name of the class that is instanciated and compare it
        # to the typename.
        # (!= meens typename is an alias to the instanciated class)
        try:
            instance = class_obj(0)  # Almost of the classes defined in
            # numpy.core.numerictypes deals with numeric types
            # constructible with just a number
        except (ValueError, TypeError):
            continue
        if instance.__class__.__name__ != t_name:
            type_alias.append((t_name, class_obj))
    return type_alias


def get_public_members(class_obj):
    """
    Return the public methods owned by the class in argument

    :return: the public methods owned by the class in argument
    :rtype: [(class_name, class_obj),...]
    """
    methods = inspect.getmembers(class_obj)
    return [meth for meth in methods if not meth[0].startswith("_")]


def get_public_methods_impl_origins(class_obj):
    """
    Returns the numpy classes where methods of a given class are
    implemented

    :param class_obj: the class which should be analyzed
    :type class_obj: class
    :return: numpy classes where methods of the given class are implemented
    :rtype: set(class, ...)
    """
    impl_origins = set()
    for _, meth_obj in get_public_members(class_obj):
        try:
            meth_obj_impl_class = meth_obj.__objclass__
        except AttributeError:
            meth_obj_impl_class = class_obj
        if inspect.getmodule(meth_obj_impl_class).__name__ == 'numpy':
            impl_origins.add(meth_obj_impl_class)
    return impl_origins


def get_pure_types():
    """
    Return all the types that are not alias inside numpy core numerictypes
    module

    :returns: all the types that are not alias inside numpy core numerictypes
    :rtype: set(class, ...)
    """
    all_types = set(get_numpy_core_numerictypes())
    alias_types = set(get_type_alias(all_types))
    return all_types - alias_types


def get_common_impl_classes():
    """
    Returns the names of the numpy classes that implement
    all the methods used by all other numpy (sub)classes

    :return: the names of the numpy classes that implement
             all the methods used by all other numpy (sub)classes
    :rtype: set(str, ...)
    """
    res = set()
    for typ in get_pure_types():
        res = res.union(get_public_methods_impl_origins(typ[1]))
    return res


def get_local_implemented_methods(class_obj):
    """
    Return the (public) methods object that are locally implemented
    inside the class in argument

    :return: (public) methods object that are locally implemented
             inside the class in argument
    :rtype: [method ...]
    """
    res = []
    for _, meth_obj in get_public_members(class_obj):
        try:
            if meth_obj.__objclass__ == class_obj:
                res.append(meth_obj)
        except AttributeError:
            res.append(meth_obj)
    return res


def get_super_classes(class_obj):
    """
    Return the super classes of the class given in argument

    :param class_obj: class from which the super classes are looked for
    :type class_obj: class
    :return: the super classes of the class given in argument
    :rtype: [class ...]
    """
    return flatten(inspect.getclasstree(inspect.getmro(class_obj)))[-1]


def flatten(target):
    try:
        return [m for l in target for m in flatten(l)]
    except TypeError:
        return target


def get_classes_deriving_from(class_obj):
    """
    Returns the classes that are deriving (directly or not) from the
    class in argument

    :param class_obj: base class
    :type class_obj: class
    :return: the classes that are deriving (directly or not) from the
             class in argument
    :rtype: [class, ...]
    """
    res = set()
    for _, typ in get_numpy_core_numerictypes():
        try:
            if class_obj in inspect.getmro(typ):
                res.add(typ)
        except AttributeError:
            continue
    return res

if __name__ == "__main__":
    impl_classes = get_common_impl_classes()
    print("There are {} classes that implement "
          "all the numpy methods:".format(len(impl_classes)))
    print(impl_classes)

    print("<-{}->".format("-" * 40))
    for cls_ in impl_classes:
        print("Class {} implements :".format(cls_))
        impl_meths = get_local_implemented_methods(cls_)
        print("\n".join([str(m) for m in impl_meths]))
        print("\n****\n")

    print("<-{}->".format("-" * 40))
    for typename, typ_obj in get_pure_types():
        super_classes = ",".join([str(m) for m in get_super_classes(typ_obj)])
        print("Class {:s} inherit from {:s}".format(typename, super_classes))

    print("<-{}->".format("-" * 40))
    for typename, typ_obj in get_type_alias(get_numpy_core_numerictypes()):
        print("Class {:s} is an alias to {}".format(typename, typ_obj))
