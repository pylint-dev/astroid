# If taking the length of a class, do not use an instance method
class F:
    def __len__(self):
        return 57
len(F)  # inferred: InferenceError
