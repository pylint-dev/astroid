import sys

from setuptools import setup


class AstroidIncompatiblePythonError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "The last version compatible with python '3.6.0' and '3.6.1' is astroid '2.6.6'"
            f"You're using {'.'.join([str(v) for v in sys.version_info[:3]])}. "
            "Please install astroid 2.6.6 explicitly or upgrade your python interpreter "
            "to at least 3.6.2. Remember that Python 3.6 end life is December 2021. "
            "See https://github.com/PyCQA/pylint/issues/5065 for more detail."
        )


if sys.version_info < (3, 6, 2):
    raise AstroidIncompatiblePythonError()
setup()
