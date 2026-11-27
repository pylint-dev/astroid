class Super(object):
   def instance(cls):
      return cls()
   instance = classmethod(instance)

class Sub(Super):
    def method(self):
        return self

# should see the Sub.instance() is returning a Sub
# instance, not a Super instance
Sub.instance().method()  # inferred: Instance(classmethod_inferred_by_context.Sub) | Uninferable
