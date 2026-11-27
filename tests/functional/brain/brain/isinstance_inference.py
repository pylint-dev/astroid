# type type
isinstance(type, type)  # inferred: Const(True)
# object type
isinstance(object, type)  # inferred: Const(True)
# type object
isinstance(type, object)  # inferred: Const(True)
# Make sure isinstance can check builtin int types
isinstance(1, int)  # inferred: Const(True)
# isinstance int false
isinstance('a', int)  # inferred: Const(False)
# Make sure isinstance can check builtin str types
isinstance('a', str)  # inferred: Const(True)
# isinstance str false
isinstance(1, str)  # inferred: Const(False)
# obj just has to be an instance of ANY class/type on the right
isinstance(1, (str, int))  # inferred: Const(True)
# isinstance type false2
isinstance(1, type)  # inferred: Const(False)
# isinstance allows bad type short-circuting
isinstance(1, (int, 1))  # inferred: Const(True)
# The second argument must be a class or a tuple of classes
isinstance(int, 1)  # inferred: InferenceError
# isinstance does not allow keywords
isinstance(1, class_or_tuple=int)  # inferred: InferenceError
# isinstance must have two arguments
isinstance(1, int, str)  # inferred: InferenceError
# first param is uninferable
isinstance(something, int)  # inferred: InferenceError
