from __future__ import unicode_literals

class MyClass(object):
    def method(self):
        "With unicode : ’ "

# +1: value.inferred.as_string(): \n\nclass MyClass(object):\n    \n    def method(self):\n        """With unicode : ’ """\n        \n
instance = MyClass()
