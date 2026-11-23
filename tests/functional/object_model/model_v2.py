# We use a generator to test this model.
def test():
   "a"
   yield

gen = test()
# +6: inferred: BoundMethod(builtins.object.__enter__)
# +5: inferred._proxied._proxied: FunctionDef(builtins.object.__enter__)
# +4: inferred._proxied._proxied.args.args: self
# +3: inferred._proxied._proxied.args.args[0].name: 'self'
# +2: inferred.bound: Generator(builtins.generator)
# +1: inferred.bound._proxied.qname(): 'builtins.generator'
gen.__enter__
# +7: inferred: BoundMethod(builtins.object.__exit__)
# +6: inferred._proxied._proxied: FunctionDef(builtins.object.__exit__)
# +5: inferred._proxied._proxied.args.args: self, exc_type, exc_value, traceback
# +4: inferred._proxied._proxied.args.args[0].name: 'self'
# +3: inferred._proxied._proxied.args.args[1].name: 'exc_type'
# +2: inferred._proxied._proxied.args.args[2].name: 'exc_value'
# +1: inferred._proxied._proxied.args.args[3].name: 'traceback'
gen.__exit__
