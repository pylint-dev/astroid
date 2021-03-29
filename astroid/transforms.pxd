import cython

@cython.final
cdef class TransformVisitor:
    cdef public object transforms

    cdef _visit(self, node)
