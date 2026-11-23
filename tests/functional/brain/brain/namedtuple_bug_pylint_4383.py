# Inference of 'NamedTuple' function shouldn't cause InferenceError.
#
# https://github.com/pylint-dev/pylint/issues/4383
if True:
    def NamedTuple():
        pass
NamedTuple  # inferred: FunctionDef(namedtuple_bug_pylint_4383.NamedTuple)
