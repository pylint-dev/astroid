# Copyright (c) 2018-2019 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy.core.umath module."""

import astroid

def numpy_core_umath_transform():
    ufunc_optional_keyword_arguments = (
        """out=None, where=True, casting='same_kind', order='K', """
        """dtype=None, subok=True"""
    )
    return astroid.parse(
        """
    # Constants
    e = 2.718281828459045
    euler_gamma = 0.5772156649015329

    # No arg functions
    def geterrobj(): return uninferable

    # One arg functions
    def seterrobj(errobj): return uninferable

    # One arg functions with optional kwargs
    def arccos(x, {opt_args:s}): return uninferable
    def arccosh(x, {opt_args:s}): return uninferable
    def arcsin(x, {opt_args:s}): return uninferable
    def arcsinh(x, {opt_args:s}): return uninferable
    def arctan(x, {opt_args:s}): return uninferable
    def arctanh(x, {opt_args:s}): return uninferable
    def cbrt(x, {opt_args:s}): return uninferable
    def conj(x, {opt_args:s}): return uninferable
    def conjugate(x, {opt_args:s}): return uninferable
    def cosh(x, {opt_args:s}): return uninferable
    def deg2rad(x, {opt_args:s}): return uninferable
    def degrees(x, {opt_args:s}): return uninferable
    def exp2(x, {opt_args:s}): return uninferable
    def expm1(x, {opt_args:s}): return uninferable
    def fabs(x, {opt_args:s}): return uninferable
    def frexp(x, {opt_args:s}): return uninferable
    def isfinite(x, {opt_args:s}): return uninferable
    def isinf(x, {opt_args:s}): return uninferable
    def log(x, {opt_args:s}): return uninferable
    def log1p(x, {opt_args:s}): return uninferable
    def log2(x, {opt_args:s}): return uninferable
    def logical_not(x, {opt_args:s}): return uninferable
    def modf(x, {opt_args:s}): return uninferable
    def negative(x, {opt_args:s}): return uninferable
    def rad2deg(x, {opt_args:s}): return uninferable
    def radians(x, {opt_args:s}): return uninferable
    def reciprocal(x, {opt_args:s}): return uninferable
    def rint(x, {opt_args:s}): return uninferable
    def sign(x, {opt_args:s}): return uninferable
    def signbit(x, {opt_args:s}): return uninferable
    def sinh(x, {opt_args:s}): return uninferable
    def spacing(x, {opt_args:s}): return uninferable
    def square(x, {opt_args:s}): return uninferable
    def tan(x, {opt_args:s}): return uninferable
    def tanh(x, {opt_args:s}): return uninferable
    def trunc(x, {opt_args:s}): return uninferable

    # Two args functions with optional kwargs
    def bitwise_and(x1, x2, {opt_args:s}): return uninferable
    def bitwise_or(x1, x2, {opt_args:s}): return uninferable
    def bitwise_xor(x1, x2, {opt_args:s}): return uninferable
    def copysign(x1, x2, {opt_args:s}): return uninferable
    def divide(x1, x2, {opt_args:s}): return uninferable
    def equal(x1, x2, {opt_args:s}): return uninferable
    def float_power(x1, x2, {opt_args:s}): return uninferable
    def floor_divide(x1, x2, {opt_args:s}): return uninferable
    def fmax(x1, x2, {opt_args:s}): return uninferable
    def fmin(x1, x2, {opt_args:s}): return uninferable
    def fmod(x1, x2, {opt_args:s}): return uninferable
    def greater(x1, x2, {opt_args:s}): return uninferable
    def hypot(x1, x2, {opt_args:s}): return uninferable
    def ldexp(x1, x2, {opt_args:s}): return uninferable
    def left_shift(x1, x2, {opt_args:s}): return uninferable
    def less(x1, x2, {opt_args:s}): return uninferable
    def logaddexp(x1, x2, {opt_args:s}): return uninferable
    def logaddexp2(x1, x2, {opt_args:s}): return uninferable
    def logical_and(x1, x2, {opt_args:s}): return numpy.ndarray([0, 0])
    def logical_or(x1, x2, {opt_args:s}): return numpy.ndarray([0, 0])
    def logical_xor(x1, x2, {opt_args:s}): return numpy.ndarray([0, 0])
    def maximum(x1, x2, {opt_args:s}): return uninferable
    def minimum(x1, x2, {opt_args:s}): return uninferable
    def nextafter(x1, x2, {opt_args:s}): return uninferable
    def not_equal(x1, x2, {opt_args:s}): return uninferable
    def power(x1, x2, {opt_args:s}): return uninferable
    def remainder(x1, x2, {opt_args:s}): return uninferable
    def right_shift(x1, x2, {opt_args:s}): return uninferable
    def subtract(x1, x2, {opt_args:s}): return uninferable
    def true_divide(x1, x2, {opt_args:s}): return uninferable
    """.format(
            opt_args=ufunc_optional_keyword_arguments
        )
    )


astroid.register_module_extender(
    astroid.MANAGER, "numpy.core.umath", numpy_core_umath_transform
)