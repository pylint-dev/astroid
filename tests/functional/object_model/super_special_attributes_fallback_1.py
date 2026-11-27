# Test that super() special attributes use the fallback path correctly.
class Base:
    def method(self):
        return super().__doc__
Base().method()  # inferred: Uninferable
