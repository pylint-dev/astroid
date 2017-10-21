# Copyright (c) 2015-2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy."""

import astroid


# TODO(cpopa): drop when understanding augmented assignments

def numpy_core_umath_transform():
    ufunc_optional_keyword_arguments = ("""out=None, where=True, casting='same_kind', order='K', """
                                        """dtype=None, subok=True""")
    return astroid.parse('''
    # Constants
    e = 2.718281828459045
    euler_gamma = 0.5772156649015329

    # No arg functions
    def geterrobj(): pass

    # One arg functions
    def seterrobj(errobj): pass

    # One arg functions with optional kwargs
    def arccos(x, {opt_args:s}): pass
    def arccosh(x, {opt_args:s}): pass
    def arcsin(x, {opt_args:s}): pass
    def arcsinh(x, {opt_args:s}): pass
    def arctan(x, {opt_args:s}): pass
    def arctanh(x, {opt_args:s}): pass
    def cbrt(x, {opt_args:s}): pass
    def conj(x, {opt_args:s}): pass
    def conjugate(x, {opt_args:s}): pass
    def cosh(x, {opt_args:s}): pass
    def deg2rad(x, {opt_args:s}): pass
    def degrees(x, {opt_args:s}): pass
    def exp2(x, {opt_args:s}): pass
    def expm1(x, {opt_args:s}): pass
    def fabs(x, {opt_args:s}): pass
    def frexp(x, {opt_args:s}): pass
    def isfinite(x, {opt_args:s}): pass
    def isinf(x, {opt_args:s}): pass
    def log(x, {opt_args:s}): pass
    def log1p(x, {opt_args:s}): pass
    def log2(x, {opt_args:s}): pass
    def logical_not(x, {opt_args:s}): pass
    def modf(x, {opt_args:s}): pass
    def negative(x, {opt_args:s}): pass
    def rad2deg(x, {opt_args:s}): pass
    def radians(x, {opt_args:s}): pass
    def reciprocal(x, {opt_args:s}): pass
    def rint(x, {opt_args:s}): pass
    def sign(x, {opt_args:s}): pass
    def signbit(x, {opt_args:s}): pass
    def sinh(x, {opt_args:s}): pass
    def spacing(x, {opt_args:s}): pass
    def square(x, {opt_args:s}): pass
    def tan(x, {opt_args:s}): pass
    def tanh(x, {opt_args:s}): pass
    def trunc(x, {opt_args:s}): pass
    
    # Two args functions with optional kwargs
    def bitwise_and(x1, x2, {opt_args:s}): pass
    def bitwise_or(x1, x2, {opt_args:s}): pass
    def bitwise_xor(x1, x2, {opt_args:s}): pass
    def copysign(x1, x2, {opt_args:s}): pass
    def divide(x1, x2, {opt_args:s}): pass
    def equal(x1, x2, {opt_args:s}): pass
    def float_power(x1, x2, {opt_args:s}): pass
    def floor_divide(x1, x2, {opt_args:s}): pass
    def fmax(x1, x2, {opt_args:s}): pass
    def fmin(x1, x2, {opt_args:s}): pass
    def fmod(x1, x2, {opt_args:s}): pass
    def greater(x1, x2, {opt_args:s}): pass
    def hypot(x1, x2, {opt_args:s}): pass
    def ldexp(x1, x2, {opt_args:s}): pass
    def left_shift(x1, x2, {opt_args:s}): pass
    def less(x1, x2, {opt_args:s}): pass
    def logaddexp(x1, x2, {opt_args:s}): pass
    def logaddexp2(x1, x2, {opt_args:s}): pass
    def logical_and(x1, x2, {opt_args:s}): pass
    def logical_or(x1, x2, {opt_args:s}): pass
    def logical_xor(x1, x2, {opt_args:s}): pass
    def maximum(x1, x2, {opt_args:s}): pass
    def minimum(x1, x2, {opt_args:s}): pass
    def nextafter(x1, x2, {opt_args:s}): pass
    def not_equal(x1, x2, {opt_args:s}): pass
    def power(x1, x2, {opt_args:s}): pass
    def remainder(x1, x2, {opt_args:s}): pass
    def right_shift(x1, x2, {opt_args:s}): pass
    def subtract(x1, x2, {opt_args:s}): pass
    def true_divide(x1, x2, {opt_args:s}): pass
    '''.format(opt_args=ufunc_optional_keyword_arguments))

def numpy_core_transform():
    return astroid.parse('''
    from numpy.core import numeric
    from numpy.core import fromnumeric
    from numpy.core import defchararray
    from numpy.core import records
    from numpy.core import function_base
    from numpy.core import machar
    from numpy.core import getlimits
    from numpy.core import shape_base
    __all__ = (['char', 'rec', 'memmap', 'chararray'] + numeric.__all__ +
               fromnumeric.__all__ +
               records.__all__ +
               function_base.__all__ +
               machar.__all__ +
               getlimits.__all__ +
               shape_base.__all__)
    ''')


def numpy_transform():
    return astroid.parse('''
    from numpy import core
    from numpy import matrixlib as _mat
    from numpy import lib
    __all__ = ['add_newdocs',
               'ModuleDeprecationWarning',
               'VisibleDeprecationWarning', 'linalg', 'fft', 'random',
               'ctypeslib', 'ma',
               '__version__', 'pkgload', 'PackageLoader',
               'show_config'] + core.__all__ + _mat.__all__ + lib.__all__

    ''')


astroid.register_module_extender(astroid.MANAGER, 'numpy.core.umath', numpy_core_umath_transform)
#astroid.register_module_extender(astroid.MANAGER, 'numpy.core', numpy_core_transform)
#astroid.register_module_extender(astroid.MANAGER, 'numpy', numpy_transform)
