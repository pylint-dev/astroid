# Regression test for issue #2721.
s = slice(-2)
@s()
@six.add_metaclass()
class a: ...  # name: 'a'
