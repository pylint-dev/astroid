class Class(object): pass
type.__new__(1, 2, 3, 4)  # inferred: InferenceError
type.__new__(Class, 2, 3, 4)  # inferred: InferenceError
