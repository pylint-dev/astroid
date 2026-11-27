from unknown import unknown
[1, 2, 3][slice(None, unknown, unknown)]  # inferred: InferenceError
[1, 2, 3][slice(None, missing, missing)]  # inferred: InferenceError
[1, 2, 3][slice(object, list, tuple)]  # inferred: InferenceError
[1, 2, 3][slice(b'a')]  # inferred: InferenceError
[1, 2, 3][slice(1, 'aa')]  # inferred: InferenceError
[1, 2, 3][slice(1, 2.0, 3.0)]  # inferred: InferenceError
[1, 2, 3][slice()]  # inferred: InferenceError
[1, 2, 3][slice(1, 2, 3, 4)]  # inferred: InferenceError
