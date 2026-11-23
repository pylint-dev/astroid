class Class(type): pass
type.__new__(Class, object, 1, 2)  # inferred: InferenceError
type.__new__(Class, 1, 1, 2)  # inferred: InferenceError
type.__new__(Class, [], 1, 2)  # inferred: InferenceError
