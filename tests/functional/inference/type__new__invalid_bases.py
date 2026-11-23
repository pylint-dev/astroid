type.__new__(type, 'a', 1, 2)  # inferred: InferenceError
type.__new__(type, 'a', [], 2)  # inferred: InferenceError
type.__new__(type, 'a', {}, 2)  # inferred: InferenceError
type.__new__(type, 'a', (1, ), 2)  # inferred: InferenceError
type.__new__(type, 'a', (object, 1), 2)  # inferred: InferenceError
