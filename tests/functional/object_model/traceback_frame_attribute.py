# The frame a traceback exposes is a data descriptor, so its value is
# unknown rather than a class named after the attribute.
#
# Closes https://github.com/pylint-dev/pylint/issues/11218
try:
    raise ValueError("a")
except ValueError as err:
    err.__traceback__.tb_frame.f_locals  # inferred: Uninferable
