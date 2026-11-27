# Regression test for https://github.com/pylint-dev/pylint/issues/7710.
import sys

sys.argv  # _infer(): Uninferable
