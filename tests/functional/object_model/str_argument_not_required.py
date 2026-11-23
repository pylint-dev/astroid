# Test that the first argument to an exception does not need to be a str.
# +2: inferred: ExceptionInstance(builtins.BaseException)
# +1: inferred.getattr(args): Instance(builtins.tuple)
BaseException()
