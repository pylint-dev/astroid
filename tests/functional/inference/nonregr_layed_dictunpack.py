# Regression test for https://github.com/pylint-dev/astroid/issues/483
# Make sure multiple dictunpack references are inferable.
base = {'data': 0}
new = {**base, 'data': 1}
new3 = {**base, **new}
new3  # inferred: Dict({'data': 1})
