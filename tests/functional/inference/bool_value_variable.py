class VariableBoolInstance(object):
    def __init__(self, value):
        self.value = value
    def __bool__(self):
        return self.value

not VariableBoolInstance(True)  # inferred: Uninferable  # inferred.bool_value: Uninferable
