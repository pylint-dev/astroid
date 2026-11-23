def test():
   "a"
   yield

gen = test()
gen.__name__  # inferred: Const('test')
gen.__doc__  # inferred: Const('a')
gen.gi_code  # inferred: Uninferable
gen.gi_frame  # inferred: Uninferable
gen.send  # inferred: BoundMethod(builtins.generator.send)
gen.__enter__  # inferred: BoundMethod(builtins.object.__enter__)
gen.__exit__  # inferred: BoundMethod(builtins.object.__exit__)
