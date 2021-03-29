import cython
from .context cimport InferenceContext

cdef dict OP_PRECEDENCE
cdef object MANAGER

cdef bint _is_const(object value)

cpdef int are_exclusive(
    stmt1, stmt2, exceptions=*
) except -1

cdef object _slice_value(object index, object context=*)

cdef tuple _find_arg(argname, args, rec=*)
cdef str _format_args(args, defaults=*, annotations=*)
cdef _container_getitem(instance, elts, index, context=*)

cdef class NodeNG:
    cdef _fixed_source_line(self)
    cpdef accept(self, visitor)
    cpdef last_child(self)
    cpdef bint parent_of(self, NodeNG node)
    cpdef NodeNG statement(self)
    cpdef frame(self)
    cpdef scope(self)
    cpdef root(self)
    cpdef child_sequence(self, child)
    cpdef locate_child(self, child)
    cpdef next_sibling(self)
    cpdef previous_sibling(self)

cdef class Statement(NodeNG):
    @cython.locals(parent=NodeNG)
    cpdef next_sibling(self)
    cpdef previous_sibling(self)
