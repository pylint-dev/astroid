# +4: handlers[0].statement().name.inferred: ExceptionInstance(builtins.ExceptionGroup)
# +3: handlers[0].statement().name.inferred.getattr(exceptions)[0]: Tuple(ExceptionInstance(builtins.ValueError))
# +2: handlers[1].statement().name.inferred: ExceptionInstance(builtins.ExceptionGroup)
# +1: handlers[1].statement().name.inferred.getattr(exceptions)[0]: Tuple(ExceptionInstance(builtins.TypeError))
try:
    raise ExceptionGroup("group", [ValueError(654), TypeError(10)])
except* ValueError as ve:
    print(e.exceptions)
except* TypeError as texc:
    print(e.exceptions)
else:
    sys.exit(127)
finally:
    sys.exit(0)
