# type type
issubclass(type, type)  # inferred: Const(True)
# object type
issubclass(object, type)  # inferred: Const(False)
# type object
issubclass(type, object)  # inferred: Const(True)
# issubclass same class
issubclass(int, int)  # inferred: Const(True)
# issubclass not the same class
issubclass(str, int)  # inferred: Const(False)
# obj just has to be a subclass of ANY class/type on the right
issubclass(int, (str, int))  # inferred: Const(True)
# issubclasss allows bad type short-circuting
issubclass(int, (int, 1))  # inferred: Const(True)
# The second argument must be a class or a tuple of classes
issubclass(int, 1)  # inferred: InferenceError
# issubclass does not allow keywords
issubclass(int, class_or_tuple=int)  # inferred: InferenceError
# issubclass must have two arguments
issubclass(int, int, str)  # inferred: InferenceError
