import cython
from .context cimport InferenceContext, CallContext

@cython.final
cdef class CallSite:
    cdef public dict argument_context_map
    cdef public set duplicated_keywords
    cdef list _unpacked_args
    cdef dict _unpacked_kwargs
    cdef public list positional_arguments
    cdef public dict keyword_arguments


    cpdef int has_invalid_arguments(self) except -1
    cpdef has_invalid_keywords(self)


    cdef dict _unpack_keywords(self, list keywords, InferenceContext context=*)
    cdef list _unpack_args(self, list args, InferenceContext context=*)

    cpdef infer_argument(self, funcnode, name, InferenceContext context)
