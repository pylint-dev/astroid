from .context cimport InferenceContext, copy_context, CallContext, bind_context_to_node
from . cimport node_classes
cdef object MANAGER
cdef object BUILTINS
cdef tuple ITER_METHODS
cdef object EXCEPTION_BASE_CLASSES
cdef object objects
cdef object BUILTIN_DESCRIPTORS

cdef list _c3_merge(list sequences, cls, InferenceContext context)
cpdef function_to_method(n, klass)
cpdef tuple builtin_lookup(str name)
