getattr(1, 'ala')  # inferred: InferenceError
getattr(int, 'ala')  # inferred: InferenceError
getattr(float, 'bala')  # inferred: InferenceError
getattr({}, 'portocala')  # inferred: InferenceError
