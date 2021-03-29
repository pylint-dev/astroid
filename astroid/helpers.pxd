from .context cimport InferenceContext, CallContext

cpdef int is_subtype(type1, type2) except -1
cpdef int is_supertype(type1, type2) except -1
cpdef bint _type_check(type1, type2) except -1
cpdef safe_infer(node, InferenceContext context=*)
cpdef object_type(node, InferenceContext context=*)
cpdef class_instance_as_index(node)
