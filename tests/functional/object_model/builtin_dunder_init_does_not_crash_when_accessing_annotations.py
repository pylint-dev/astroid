class Class:
    @classmethod
    def class_method(cls):
        cls.__init__.__annotations__  # inferred: Dict({})  # inferred.items: []
