class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1  # inferred: Const(1) | Uninferable
