class Changer:
    def __getattribute__(self, name):
        list_collection.append(self)
        set_collection.add(self)
        dict_collection[self] = self
        return object.__getattribute__(self, name)


list_collection = [Changer()]
set_collection = {Changer()}
dict_collection = {Changer(): Changer()}
