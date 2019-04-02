# Copyright (c) 2015-2016, 2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2016 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2017-2018 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy."""

import functools
import astroid


def infer_numpy_ndarray(node, context=None):
    ndarray = """
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

        def __abs__(self): return numpy.ndarray([0, 0])
        def __add__(self, value): return numpy.ndarray([0, 0]) 
        def __and__(self, value): return numpy.ndarray([0, 0]) 
        def __array__(dtype=None): return numpy.ndarray([0, 0]) 
        def __array_wrap__(obj): return numpy.ndarray([0, 0]) 
        def __contains__(self, key): return uninferable
        def __copy__(self): return numpy.ndarray([0, 0])
        def __deepcopy__(self, memo): return numpy.ndarray([0, 0])
        def __divmod__(self, value): return (numpy.ndarray([0, 0]), numpy.ndarray([0, 0]))
        def __eq__(self, value): return numpy.ndarray([0, 0])
        def __float__(self): return 0.
        def __floordiv__(self): return numpy.ndarray([0, 0])
        def __ge__(self, value): return numpy.ndarray([0, 0])
        def __getitem__(self, key): return uninferable
        def __gt__(self, value): return numpy.ndarray([0, 0])
        def __iadd__(self, value): return numpy.ndarray([0, 0])
        def __iand__(self, value): return numpy.ndarray([0, 0])
        def __ifloordiv__(self, value): return numpy.ndarray([0, 0])
        def __ilshift__(self, value): return numpy.ndarray([0, 0])
        def __imod__(self, value): return numpy.ndarray([0, 0])
        def __imul__(self, value): return numpy.ndarray([0, 0])
        def __int__(self): return 0
        def __invert__(self): return numpy.ndarray([0, 0])
        def __ior__(self, value): return numpy.ndarray([0, 0])
        def __ipow__(self, value): return numpy.ndarray([0, 0])
        def __irshift__(self, value): return numpy.ndarray([0, 0])
        def __isub__(self, value): return numpy.ndarray([0, 0])
        def __itruediv__(self, value): return numpy.ndarray([0, 0])
        def __ixor__(self, value): return numpy.ndarray([0, 0])
        def __le__(self, value): return numpy.ndarray([0, 0])
        def __len__(self): return 1
        def __lshift__(self, value): return numpy.ndarray([0, 0])
        def __lt__(self, value): return numpy.ndarray([0, 0])
        def __matmul__(self, value): return numpy.ndarray([0, 0])
        def __mod__(self, value): return numpy.ndarray([0, 0])
        def __mul__(self, value): return numpy.ndarray([0, 0])
        def __ne__(self, value): return numpy.ndarray([0, 0])
        def __neg__(self): return numpy.ndarray([0, 0])
        def __or__(self): return numpy.ndarray([0, 0])
        def __pos__(self): return numpy.ndarray([0, 0])
        def __pow__(self): return numpy.ndarray([0, 0])
        def __repr__(self): return str()
        def __rshift__(self): return numpy.ndarray([0, 0])
        def __setitem__(self, key, value): return uninferable
        def __str__(self): return str()
        def __sub__(self, value): return numpy.ndarray([0, 0])
        def __truediv__(self, value): return numpy.ndarray([0, 0])
        def __xor__(self, value): return numpy.ndarray([0, 0])
        def __inv__(self): return uninferable
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
        def itemset(self, *args): return None
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
    """
    node = astroid.extract_node(ndarray)
    return node.infer(context=context)

def _looks_like_numpy_ndarray(node):
    return isinstance(node, astroid.Attribute) and node.attrname == 'ndarray'

astroid.MANAGER.register_transform(
    astroid.Attribute,
    astroid.inference_tip(infer_numpy_ndarray),
    _looks_like_numpy_ndarray
)