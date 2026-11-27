# Test that random.sample does not crash when cloning FunctionDef nodes.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/2923
import random
# +1: inferred: List(FunctionDef(no_crash_on_functiondef_clone.len))
random.sample([len] * 2, 1)
