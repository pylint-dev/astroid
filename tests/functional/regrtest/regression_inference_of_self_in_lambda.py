class A:
    @b(lambda self: __(self))  # inferred: Instance(regression_inference_of_self_in_lambda.A)
    def d(self):
        pass
