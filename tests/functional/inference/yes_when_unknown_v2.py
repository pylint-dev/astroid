from missing import Missing
getattr(1, Unknown)  # inferred: InferenceError
getattr(Unknown, 'a')  # inferred: InferenceError
getattr(Unknown, Unknown)  # inferred: InferenceError
getattr(Unknown, Unknown, Unknown)  # inferred: InferenceError

getattr(Missing, 'a')  # inferred: Uninferable
getattr(Missing, Missing)  # inferred: Uninferable
getattr('a', Missing)  # inferred: Uninferable
getattr('a', Missing, Missing)  # inferred: Uninferable
