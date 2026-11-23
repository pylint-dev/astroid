class A:
    __pos__ = (i for i in range(10))
+A()  # inferred: InferenceError
