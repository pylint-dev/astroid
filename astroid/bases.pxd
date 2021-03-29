from .context cimport InferenceContext, bind_context_to_node, CallContext

cdef set PROPERTIES
cdef set POSSIBLE_PROPERTIES
cdef object MANAGER
