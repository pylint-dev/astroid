class A(object):
    def __getitem__(self, index):
        return index
A()[1:]  # inferred: Slice  # inferred.lower.value: 1  # inferred.upper: None
