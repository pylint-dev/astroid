class PropertyWithSetter:
    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = value

# +1: inferred: BoundMethod(infer_property_setter.PropertyWithSetter.host) | Uninferable
PropertyWithSetter().host
