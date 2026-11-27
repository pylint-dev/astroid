class APropert():
    @property
    def property(self):
        return self
APropert().property  # inferred: Instance(recursive_property_method.APropert)
