def gen(): yield
GEN = gen()
next(GEN)  # inferred: InferenceError
