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
    def beta(a, b, size=None): return any
    def binomial(n, p, size=None): return any
    def bytes(length): return any
    def chisquare(df, size=None): return any
    def choice(a, size=None, replace=True, p=None): return any
    def dirichlet(alpha, size=None): return any
    def exponential(scale=1.0, size=None): return any
    def f(dfnum, dfden, size=None): return any
    def gamma(shape, scale=1.0, size=None): return any
    def geometric(p, size=None): return any
    def get_state(): return any
    def gumbel(loc=0.0, scale=1.0, size=None): return any
    def hypergeometric(ngood, nbad, nsample, size=None): return any
    def laplace(loc=0.0, scale=1.0, size=None): return any
    def logistic(loc=0.0, scale=1.0, size=None): return any
    def lognormal(mean=0.0, sigma=1.0, size=None): return any
    def logseries(p, size=None): return any
    def multinomial(n, pvals, size=None): return any
    def multivariate_normal(mean, cov, size=None): return any
    def negative_binomial(n, p, size=None): return any
    def noncentral_chisquare(df, nonc, size=None): return any
    def noncentral_f(dfnum, dfden, nonc, size=None): return any
    def normal(loc=0.0, scale=1.0, size=None): return any
    def pareto(a, size=None): return any
    def permutation(x): return any
    def poisson(lam=1.0, size=None): return any
    def power(a, size=None): return any
    def rand(*args): return any
    def randint(low, high=None, size=None, dtype='l'): return any
    def randn(*args): return any
    def random_integers(low, high=None, size=None): return any
    def random_sample(size=None): return any
    def rayleigh(scale=1.0, size=None): return any
    def seed(seed=None): return any
    def set_state(state): return any
    def shuffle(x): return any
    def standard_cauchy(size=None): return any
    def standard_exponential(size=None): return any
    def standard_gamma(shape, size=None): return any
    def standard_normal(size=None): return any
    def standard_t(df, size=None): return any
    def triangular(left, mode, right, size=None): return any
    def uniform(low=0.0, high=1.0, size=None): return any
    def vonmises(mu, kappa, size=None): return any
    def wald(mean, scale, size=None): return any
    def weibull(a, size=None): return any
    def zipf(a, size=None): return any
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
    def geterrobj(): return any

    # One arg functions
    def seterrobj(errobj): return any

    # One arg functions with optional kwargs
    def arccos(x, {opt_args:s}): return any
    def arccosh(x, {opt_args:s}): return any
    def arcsin(x, {opt_args:s}): return any
    def arcsinh(x, {opt_args:s}): return any
    def arctan(x, {opt_args:s}): return any
    def arctanh(x, {opt_args:s}): return any
    def cbrt(x, {opt_args:s}): return any
    def conj(x, {opt_args:s}): return any
    def conjugate(x, {opt_args:s}): return any
    def cosh(x, {opt_args:s}): return any
    def deg2rad(x, {opt_args:s}): return any
    def degrees(x, {opt_args:s}): return any
    def exp2(x, {opt_args:s}): return any
    def expm1(x, {opt_args:s}): return any
    def fabs(x, {opt_args:s}): return any
    def frexp(x, {opt_args:s}): return any
    def isfinite(x, {opt_args:s}): return any
    def isinf(x, {opt_args:s}): return any
    def log(x, {opt_args:s}): return any
    def log1p(x, {opt_args:s}): return any
    def log2(x, {opt_args:s}): return any
    def logical_not(x, {opt_args:s}): return any
    def modf(x, {opt_args:s}): return any
    def negative(x, {opt_args:s}): return any
    def rad2deg(x, {opt_args:s}): return any
    def radians(x, {opt_args:s}): return any
    def reciprocal(x, {opt_args:s}): return any
    def rint(x, {opt_args:s}): return any
    def sign(x, {opt_args:s}): return any
    def signbit(x, {opt_args:s}): return any
    def sinh(x, {opt_args:s}): return any
    def spacing(x, {opt_args:s}): return any
    def square(x, {opt_args:s}): return any
    def tan(x, {opt_args:s}): return any
    def tanh(x, {opt_args:s}): return any
    def trunc(x, {opt_args:s}): return any

    # Two args functions with optional kwargs
    def bitwise_and(x1, x2, {opt_args:s}): return any
    def bitwise_or(x1, x2, {opt_args:s}): return any
    def bitwise_xor(x1, x2, {opt_args:s}): return any
    def copysign(x1, x2, {opt_args:s}): return any
    def divide(x1, x2, {opt_args:s}): return any
    def equal(x1, x2, {opt_args:s}): return any
    def float_power(x1, x2, {opt_args:s}): return any
    def floor_divide(x1, x2, {opt_args:s}): return any
    def fmax(x1, x2, {opt_args:s}): return any
    def fmin(x1, x2, {opt_args:s}): return any
    def fmod(x1, x2, {opt_args:s}): return any
    def greater(x1, x2, {opt_args:s}): return any
    def hypot(x1, x2, {opt_args:s}): return any
    def ldexp(x1, x2, {opt_args:s}): return any
    def left_shift(x1, x2, {opt_args:s}): return any
    def less(x1, x2, {opt_args:s}): return any
    def logaddexp(x1, x2, {opt_args:s}): return any
    def logaddexp2(x1, x2, {opt_args:s}): return any
    def logical_and(x1, x2, {opt_args:s}): return any
    def logical_or(x1, x2, {opt_args:s}): return any
    def logical_xor(x1, x2, {opt_args:s}): return any
    def maximum(x1, x2, {opt_args:s}): return any
    def minimum(x1, x2, {opt_args:s}): return any
    def nextafter(x1, x2, {opt_args:s}): return any
    def not_equal(x1, x2, {opt_args:s}): return any
    def power(x1, x2, {opt_args:s}): return any
    def remainder(x1, x2, {opt_args:s}): return any
    def right_shift(x1, x2, {opt_args:s}): return any
    def subtract(x1, x2, {opt_args:s}): return any
    def true_divide(x1, x2, {opt_args:s}): return any
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

        def all(self): return any
        def any(self): return any
        def argmax(self): return any
        def argmin(self): return any
        def argsort(self): return any
        def astype(self): return any
        def base(self): return any
        def byteswap(self): return any
        def choose(self): return any
        def clip(self): return any
        def compress(self): return any
        def conj(self): return any
        def conjugate(self): return any
        def copy(self): return any
        def cumprod(self): return any
        def cumsum(self): return any
        def data(self): return any
        def diagonal(self): return any
        def dtype(self): return any
        def dump(self): return any
        def dumps(self): return any
        def fill(self): return any
        def flags(self): return any
        def flat(self): return any
        def flatten(self): return any
        def getfield(self): return any
        def imag(self): return any
        def item(self): return any
        def itemset(self): return any
        def itemsize(self): return any
        def max(self): return any
        def mean(self): return any
        def min(self): return any
        def nbytes(self): return any
        def ndim(self): return any
        def newbyteorder(self): return any
        def nonzero(self): return any
        def prod(self): return any
        def ptp(self): return any
        def put(self): return any
        def ravel(self): return any
        def real(self): return any
        def repeat(self): return any
        def reshape(self): return any
        def resize(self): return any
        def round(self): return any
        def searchsorted(self): return any
        def setfield(self): return any
        def setflags(self): return any
        def shape(self): return any
        def size(self): return any
        def sort(self): return any
        def squeeze(self): return any
        def std(self): return any
        def strides(self): return any
        def sum(self): return any
        def swapaxes(self): return any
        def take(self): return any
        def tobytes(self): return any
        def tofile(self): return any
        def tolist(self): return any
        def tostring(self): return any
        def trace(self): return any
        def transpose(self): return any
        def var(self): return any
        def view(self): return any


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

        def newbyteorder(self, new_order='S'): return any
        def __neg__(self): return any


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

        def __neg__(self): return any
        def __inv__(self): return any
        def __invert__(self): return any
        def all(self): return any
        def any(self): return any
        def argmax(self): return any
        def argmin(self): return any
        def argpartition(self): return any
        def argsort(self): return any
        def astype(self): return any
        def byteswap(self): return any
        def choose(self): return any
        def clip(self): return any
        def compress(self): return any
        def conj(self): return any
        def conjugate(self): return any
        def copy(self): return any
        def cumprod(self): return any
        def cumsum(self): return any
        def diagonal(self): return any
        def dot(self): return any
        def dump(self): return any
        def dumps(self): return any
        def fill(self): return any
        def flatten(self): return any
        def getfield(self): return any
        def item(self): return any
        def itemset(self): return any
        def max(self): return any
        def mean(self): return any
        def min(self): return any
        def newbyteorder(self): return any
        def nonzero(self): return any
        def partition(self): return any
        def prod(self): return any
        def ptp(self): return any
        def put(self): return any
        def ravel(self): return any
        def repeat(self): return any
        def reshape(self): return any
        def resize(self): return any
        def round(self): return any
        def searchsorted(self): return any
        def setfield(self): return any
        def setflags(self): return any
        def sort(self): return any
        def squeeze(self): return any
        def std(self): return any
        def sum(self): return any
        def swapaxes(self): return any
        def take(self): return any
        def tobytes(self): return any
        def tofile(self): return any
        def tolist(self): return any
        def tostring(self): return any
        def trace(self): return any
        def transpose(self): return any
        def var(self): return any
        def view(self): return any


    class busdaycalendar(object):
        def __init__(self, weekmask='1111100', holidays=None):
            self.holidays = None
            self.weekmask = None

    class flexible(generic): pass
    class bool_(generic): pass
    class number(generic):
        def __neg__(self): return any
    class datetime64(generic): pass


    class void(flexible):
        def __init__(self, *args, **kwargs):
            self.base = None
            self.dtype = None
            self.flags = None
        def getfield(self): return any
        def setfield(self): return any


    class character(flexible): pass


    class integer(number):
        def __init__(self, value):
           self.denominator = None
           self.numerator = None


    class inexact(number): pass


    class str_(str, character):
        def maketrans(self, x, y=None, z=None): return any


    class bytes_(bytes, character):
        def fromhex(self, string): return any
        def maketrans(self, frm, to): return any


    class signedinteger(integer): pass


    class unsignedinteger(integer): pass


    class complexfloating(inexact): pass


    class floating(inexact): pass


    class float64(floating, float):
        def fromhex(self, string): return any


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
