def gen():
    yield 'a'
    yield 'b'
len(gen())  # inferred: InferenceError
