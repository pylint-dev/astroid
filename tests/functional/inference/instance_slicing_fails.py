class A(object):
    def __getitem__(self, index):
        return 1[index]
A()[4:5]  # inferred: Uninferable
A()[2:]  # inferred: Uninferable
