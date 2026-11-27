import collections
collections_module = collections  # inferred: Module(collections)  # inferred.bool_value(): True
def function(): pass  # bool_value(): True
class Class(object):  # bool_value(): True
    def method(self): pass
dict_comp = {x:y for (x, y) in ((1, 2), (2, 3))}  # inferred: Uninferable
set_comp = {x for x in range(10)}  # inferred: Uninferable
list_comp = [x for x in range(10)]  # inferred: Uninferable
lambda_func = lambda: None  # inferred: Lambda(bool_value.<lambda>)
unbound_method = Class.method  # inferred: UnboundMethod(bool_value.Class.method)
instance = Class()
bound_method = instance.method  # inferred: BoundMethod(bool_value.Class.method)
def generator_func():
     yield
def true_value():
     return True
generator = generator_func()  # inferred: Generator(builtins.generator)
bin_op = 1 + 2  # value.bool_value(): Uninferable
bool_op = x and y  # value.bool_value(): Uninferable
callfunc = test()  # value.bool_value(): Uninferable
good_callfunc = true_value()  # inferred: Const(True)  # inferred.bool_value(): True
compare = 2 < 3  # value.bool_value(): Uninferable
const_str_true = 'testconst'
const_str_false = ''
