from .context cimport InferenceContext, copy_context, CallContext, bind_context_to_node
from .helpers cimport is_subtype, is_supertype, safe_infer, object_type, class_instance_as_index

cdef object MANAGER

cdef list _infer_sequence_helper(node, InferenceContext context=*)
cdef dict _update_with_replacement(dict lhs_dict, dict rhs_dict)
cdef _higher_function_scope(node)
# cdef int _is_not_implemented(const) except -1
cdef _invoke_binop_inference(instance, opnode, op, other, InferenceContext context, method_name)
cdef _aug_op(instance, opnode, op, other, InferenceContext context, bint reverse=*)
cdef _bin_op(instance, opnode, op, other, InferenceContext context, reverse=*)
cdef int _same_type(type1, type2) except -1
cdef list _get_binop_flow(
    left, left_type, binary_opnode, right, right_type, InferenceContext context, reverse_context
)

cdef dict _populate_context_lookup(call, InferenceContext context)

cdef object _SUBSCRIPT_SENTINEL


