class First(object):
    def method(self):
        pass
    @classmethod
    def class_method(cls):
        pass
class Super_Type_Type(First):
    def method(self):
        # +1: inferred: FunctionDef(super_bound_model.First.method)
        super(Super_Type_Type, Super_Type_Type).method
        # +3: inferred: BoundMethod(super_bound_model.First.class_method)
        # +2: inferred.bound.name: 'First'
        # +1: inferred.type: 'classmethod'
        super(Super_Type_Type, Super_Type_Type).class_method
    @classmethod
    def class_method(cls):
        # +1: inferred: FunctionDef(super_bound_model.First.method)
        super(Super_Type_Type, Super_Type_Type).method
        # +3: inferred: BoundMethod(super_bound_model.First.class_method)
        # +2: inferred.bound.name: 'First'
        # +1: inferred.type: 'classmethod'
        super(Super_Type_Type, Super_Type_Type).class_method

class Super_Type_Object(First):
    def method(self):
        # +3: inferred: BoundMethod(super_bound_model.First.method)
        # +2: inferred.bound.name: 'First'
        # +1: inferred.type: 'method'
        super(Super_Type_Object, self).method
        # +3: inferred: BoundMethod(super_bound_model.First.class_method)
        # +2: inferred.bound.name: 'First'
        # +1: inferred.type: 'classmethod'
        super(Super_Type_Object, self).class_method
