class MyClass:
    def __init__(self):
        self._slice = slice(0, 10)

    def incr(self):
        self._slice = slice(0, self._slice.stop + 1)

    def test(self):
        self._slice  # inferred: Instance(builtins.slice) | Slice
