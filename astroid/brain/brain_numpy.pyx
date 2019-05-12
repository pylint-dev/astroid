# Copyright (c) 2015-2016, 2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2017-2018 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy."""

import functools
import astroid


def numpy_random_mtrand_transform():
    return astroid.parse(
        """
    def beta(a, b, size=None): return uninferable
    def binomial(n, p, size=None): return uninferable
    def bytes(length): return uninferable
    def chisquare(df, size=None): return uninferable
    def choice(a, size=None, replace=True, p=None): return uninferable
    def dirichlet(alpha, size=None): return uninferable
    def exponential(scale=1.0, size=None): return uninferable
    def f(dfnum, dfden, size=None): return uninferable
    def gamma(shape, scale=1.0, size=None): return uninferable
    def geometric(p, size=None): return uninferable
    def get_state(): return uninferable
    def gumbel(loc=0.0, scale=1.0, size=None): return uninferable
    def hypergeometric(ngood, nbad, nsample, size=None): return uninferable
    def laplace(loc=0.0, scale=1.0, size=None): return uninferable
    def logistic(loc=0.0, scale=1.0, size=None): return uninferable
    def lognormal(mean=0.0, sigma=1.0, size=None): return uninferable
    def logseries(p, size=None): return uninferable
    def multinomial(n, pvals, size=None): return uninferable
    def multivariate_normal(mean, cov, size=None): return uninferable
    def negative_binomial(n, p, size=None): return uninferable
    def noncentral_chisquare(df, nonc, size=None): return uninferable
    def noncentral_f(dfnum, dfden, nonc, size=None): return uninferable
    def normal(loc=0.0, scale=1.0, size=None): return uninferable
    def pareto(a, size=None): return uninferable
    def permutation(x): return uninferable
    def poisson(lam=1.0, size=None): return uninferable
    def power(a, size=None): return uninferable
    def rand(*args): return uninferable
    def randint(low, high=None, size=None, dtype='l'): return uninferable
    def randn(*args): return uninferable
    def random_integers(low, high=None, size=None): return uninferable
    def random_sample(size=None): return uninferable
    def rayleigh(scale=1.0, size=None): return uninferable
    def seed(seed=None): return uninferable
    def set_state(state): return uninferable
    def shuffle(x): return uninferable
    def standard_cauchy(size=None): return uninferable
    def standard_exponential(size=None): return uninferable
    def standard_gamma(shape, size=None): return uninferable
    def standard_normal(size=None): return uninferable
    def standard_t(df, size=None): return uninferable
    def triangular(left, mode, right, size=None): return uninferable
    def uniform(low=0.0, high=1.0, size=None): return uninferable
    def vonmises(mu, kappa, size=None): return uninferable
    def wald(mean, scale, size=None): return uninferable
    def weibull(a, size=None): return uninferable
    def zipf(a, size=None): return uninferable
    """
    )


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
    def logical_and(x1, x2, {opt_args:s}): return uninferable
    def logical_or(x1, x2, {opt_args:s}): return uninferable
    def logical_xor(x1, x2, {opt_args:s}): return uninferable
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


def numpy_core_numerictypes_transform():
    return astroid.parse(
        """
    # different types defined in numerictypes.py
    class generic(object):
        def __init__(self, value):
            self.T = None
            self.base = None
            self.data = None
            self.dtype = None
            self.flags = None
            self.flat = None
            self.imag = None
            self.itemsize = None
            self.nbytes = None
            self.ndim = None
            self.real = None
            self.size = None
            self.strides = None

        def all(self): return uninferable
        def any(self): return uninferable
        def argmax(self): return uninferable
        def argmin(self): return uninferable
        def argsort(self): return uninferable
        def astype(self): return uninferable
        def base(self): return uninferable
        def byteswap(self): return uninferable
        def choose(self): return uninferable
        def clip(self): return uninferable
        def compress(self): return uninferable
        def conj(self): return uninferable
        def conjugate(self): return uninferable
        def copy(self): return uninferable
        def cumprod(self): return uninferable
        def cumsum(self): return uninferable
        def data(self): return uninferable
        def diagonal(self): return uninferable
        def dtype(self): return uninferable
        def dump(self): return uninferable
        def dumps(self): return uninferable
        def fill(self): return uninferable
        def flags(self): return uninferable
        def flat(self): return uninferable
        def flatten(self): return uninferable
        def getfield(self): return uninferable
        def imag(self): return uninferable
        def item(self): return uninferable
        def itemset(self): return uninferable
        def itemsize(self): return uninferable
        def max(self): return uninferable
        def mean(self): return uninferable
        def min(self): return uninferable
        def nbytes(self): return uninferable
        def ndim(self): return uninferable
        def newbyteorder(self): return uninferable
        def nonzero(self): return uninferable
        def prod(self): return uninferable
        def ptp(self): return uninferable
        def put(self): return uninferable
        def ravel(self): return uninferable
        def real(self): return uninferable
        def repeat(self): return uninferable
        def reshape(self): return uninferable
        def resize(self): return uninferable
        def round(self): return uninferable
        def searchsorted(self): return uninferable
        def setfield(self): return uninferable
        def setflags(self): return uninferable
        def shape(self): return uninferable
        def size(self): return uninferable
        def sort(self): return uninferable
        def squeeze(self): return uninferable
        def std(self): return uninferable
        def strides(self): return uninferable
        def sum(self): return uninferable
        def swapaxes(self): return uninferable
        def take(self): return uninferable
        def tobytes(self): return uninferable
        def tofile(self): return uninferable
        def tolist(self): return uninferable
        def tostring(self): return uninferable
        def trace(self): return uninferable
        def transpose(self): return uninferable
        def var(self): return uninferable
        def view(self): return uninferable


    class dtype(object):
        def __init__(self, obj, align=False, copy=False):
            self.alignment = None
            self.base = None
            self.byteorder = None
            self.char = None
            self.descr = None
            self.fields = None
            self.flags = None
            self.hasobject = None
            self.isalignedstruct = None
            self.isbuiltin = None
            self.isnative = None
            self.itemsize = None
            self.kind = None
            self.metadata = None
            self.name = None
            self.names = None
            self.num = None
            self.shape = None
            self.str = None
            self.subdtype = None
            self.type = None

        def newbyteorder(self, new_order='S'): return uninferable
        def __neg__(self): return uninferable


    class ndarray(object):
        def __init__(self, shape, dtype=float, buffer=None, offset=0,
                     strides=None, order=None):
            self.T = None
            self.base = None
            self.ctypes = None
            self.data = None
            self.dtype = None
            self.flags = None
            self.flat = None
            self.imag = None
            self.itemsize = None
            self.nbytes = None
            self.ndim = None
            self.real = None
            self.shape = None
            self.size = None
            self.strides = None

        def __neg__(self): return uninferable
        def __inv__(self): return uninferable
        def __invert__(self): return uninferable
        def all(self): return uninferable
        def any(self): return uninferable
        def argmax(self): return uninferable
        def argmin(self): return uninferable
        def argpartition(self): return uninferable
        def argsort(self): return uninferable
        def astype(self): return uninferable
        def byteswap(self): return uninferable
        def choose(self): return uninferable
        def clip(self): return uninferable
        def compress(self): return uninferable
        def conj(self): return uninferable
        def conjugate(self): return uninferable
        def copy(self): return uninferable
        def cumprod(self): return uninferable
        def cumsum(self): return uninferable
        def diagonal(self): return uninferable
        def dot(self): return uninferable
        def dump(self): return uninferable
        def dumps(self): return uninferable
        def fill(self): return uninferable
        def flatten(self): return uninferable
        def getfield(self): return uninferable
        def item(self): return uninferable
        def itemset(self): return uninferable
        def max(self): return uninferable
        def mean(self): return uninferable
        def min(self): return uninferable
        def newbyteorder(self): return uninferable
        def nonzero(self): return uninferable
        def partition(self): return uninferable
        def prod(self): return uninferable
        def ptp(self): return uninferable
        def put(self): return uninferable
        def ravel(self): return uninferable
        def repeat(self): return uninferable
        def reshape(self): return uninferable
        def resize(self): return uninferable
        def round(self): return uninferable
        def searchsorted(self): return uninferable
        def setfield(self): return uninferable
        def setflags(self): return uninferable
        def sort(self): return uninferable
        def squeeze(self): return uninferable
        def std(self): return uninferable
        def sum(self): return uninferable
        def swapaxes(self): return uninferable
        def take(self): return uninferable
        def tobytes(self): return uninferable
        def tofile(self): return uninferable
        def tolist(self): return uninferable
        def tostring(self): return uninferable
        def trace(self): return uninferable
        def transpose(self): return uninferable
        def var(self): return uninferable
        def view(self): return uninferable


    class busdaycalendar(object):
        def __init__(self, weekmask='1111100', holidays=None):
            self.holidays = None
            self.weekmask = None

    class flexible(generic): pass
    class bool_(generic): pass
    class number(generic):
        def __neg__(self): return uninferable
    class datetime64(generic): pass


    class void(flexible):
        def __init__(self, *args, **kwargs):
            self.base = None
            self.dtype = None
            self.flags = None
        def getfield(self): return uninferable
        def setfield(self): return uninferable


    class character(flexible): pass


    class integer(number):
        def __init__(self, value):
           self.denominator = None
           self.numerator = None


    class inexact(number): pass


    class str_(str, character):
        def maketrans(self, x, y=None, z=None): return uninferable


    class bytes_(bytes, character):
        def fromhex(self, string): return uninferable
        def maketrans(self, frm, to): return uninferable


    class signedinteger(integer): pass


    class unsignedinteger(integer): pass


    class complexfloating(inexact): pass


    class floating(inexact): pass


    class float64(floating, float):
        def fromhex(self, string): return uninferable


    class uint64(unsignedinteger): pass
    class complex64(complexfloating): pass
    class int16(signedinteger): pass
    class float96(floating): pass
    class int8(signedinteger): pass
    class uint32(unsignedinteger): pass
    class uint8(unsignedinteger): pass
    class _typedict(dict): pass
    class complex192(complexfloating): pass
    class timedelta64(signedinteger): pass
    class int32(signedinteger): pass
    class uint16(unsignedinteger): pass
    class float32(floating): pass
    class complex128(complexfloating, complex): pass
    class float16(floating): pass
    class int64(signedinteger): pass

    buffer_type = memoryview
    bool8 = bool_
    byte = int8
    bytes0 = bytes_
    cdouble = complex128
    cfloat = complex128
    clongdouble = complex192
    clongfloat = complex192
    complex_ = complex128
    csingle = complex64
    double = float64
    float_ = float64
    half = float16
    int0 = int32
    int_ = int32
    intc = int32
    intp = int32
    long = int32
    longcomplex = complex192
    longdouble = float96
    longfloat = float96
    longlong = int64
    object0 = object_
    object_ = object_
    short = int16
    single = float32
    singlecomplex = complex64
    str0 = str_
    string_ = bytes_
    ubyte = uint8
    uint = uint32
    uint0 = uint32
    uintc = uint32
    uintp = uint32
    ulonglong = uint64
    unicode = str_
    unicode_ = str_
    ushort = uint16
    void0 = void
    """
    )


def numpy_funcs():
    return astroid.parse(
        """
    import builtins
    def sum(a, axis=None, dtype=None, out=None, keepdims=None):
        return builtins.sum(a)
    """
    )


def _looks_like_numpy_function(func_name, numpy_module_name, node):
    """
    Return True if the current node correspond to the function inside
    the numpy module in parameters

    :param node: the current node
    :type node: FunctionDef
    :param func_name: name of the function
    :type func_name: str
    :param numpy_module_name: name of the numpy module
    :type numpy_module_name: str
    :return: True if the current node correspond to the function looked for
    :rtype: bool
    """
    return node.name == func_name and node.parent.name == numpy_module_name


def numpy_function_infer_call_result(node):
    """
    A wrapper around infer_call_result method bounded to the node.

    :param node: the node which infer_call_result should be filtered
    :type node: FunctionDef
    :return: a function that filter the results of the call to node.infer_call_result
    :rtype: function
    """
    #  Put the origin infer_call_result method into the closure
    origin_infer_call_result = node.infer_call_result

    def infer_call_result_wrapper(caller=None, context=None):
        """
        Call the origin infer_call_result method bounded to the node instance and
        filter the results to remove List and Tuple instances
        """
        unfiltered_infer_call_result = origin_infer_call_result(caller, context)
        return (
            x
            for x in unfiltered_infer_call_result
            if not isinstance(x, (astroid.List, astroid.Tuple))
        )

    return infer_call_result_wrapper


def _replace_numpy_function_infer_call_result(node, context=None):
    node.infer_call_result = numpy_function_infer_call_result(node)
    return


astroid.MANAGER.register_transform(
    astroid.FunctionDef,
    _replace_numpy_function_infer_call_result,
    functools.partial(
        _looks_like_numpy_function, "linspace", "numpy.core.function_base"
    ),
)

astroid.MANAGER.register_transform(
    astroid.FunctionDef,
    _replace_numpy_function_infer_call_result,
    functools.partial(_looks_like_numpy_function, "array", "numpy.core.records"),
)

astroid.register_module_extender(
    astroid.MANAGER, "numpy.core.umath", numpy_core_umath_transform
)
astroid.register_module_extender(
    astroid.MANAGER, "numpy.random.mtrand", numpy_random_mtrand_transform
)
astroid.register_module_extender(
    astroid.MANAGER, "numpy.core.numerictypes", numpy_core_numerictypes_transform
)
astroid.register_module_extender(astroid.MANAGER, "numpy", numpy_funcs)
