def MixinFactory(cls):
    mixin_name = '{}Mixin'.format(cls.__name__)
    mixin_bases = (object,)
    mixin_attrs = {}
    mixin = type(mixin_name, mixin_bases, mixin_attrs)
    return mixin
class MixinA(MixinFactory(int)):
    pass
class MixinB(MixinFactory(str)):
    pass
class Base(object):
    pass
class ClassA(MixinA, Base):
    pass
class ClassB(MixinB, ClassA):
    pass
# +1: mro: mro_with_factories.FinalClass, mro_with_factories.ClassB, mro_with_factories.MixinB, mro_with_factories.MixinFactory.strMixin, mro_with_factories.ClassA, mro_with_factories.MixinA, mro_with_factories.MixinFactory.intMixin, mro_with_factories.Base, builtins.object
class FinalClass(ClassB):
    def __init__(self):
        self.name = 'x'
