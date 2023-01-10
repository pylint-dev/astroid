class Broken:

    def __getattr__(self, name):
        raise Exception("boom")


broken = Broken()
