# Test that random.sample does not crash when cloning ClassDef nodes.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/2923
import random
# +1: inferred: List(ClassDef(no_crash_on_classdef_clone.dict))
random.sample([dict] * 2, 1)
