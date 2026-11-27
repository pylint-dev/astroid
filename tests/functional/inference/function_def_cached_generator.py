# Regression test for https://github.com/pylint-dev/astroid/issues/817.
def func(): pass  # _infer(): FunctionDef(function_def_cached_generator.func)
