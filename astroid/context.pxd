import cython

@cython.final
cdef class InferenceContext:
    cdef public set path
    cdef public str lookupname
    cdef public CallContext callcontext
    cdef public object boundnode
    cdef public dict inferred
    cdef public dict extra_context

    cpdef int push(self, node) except -1
    cpdef InferenceContext clone(self)


@cython.final
cdef class CallContext:
    cdef public list args
    cdef public list keywords

cpdef InferenceContext copy_context(InferenceContext context)

cpdef InferenceContext bind_context_to_node(InferenceContext context, node)
