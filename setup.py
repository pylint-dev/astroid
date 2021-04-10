from pathlib import Path

from setuptools import setup

pkginfo = Path(__file__).parent / "astroid/__pkginfo__.py"

with open(pkginfo, "rb") as fobj:
    exec(compile(fobj.read(), pkginfo, "exec"), locals())  # pylint: disable=exec-used

setup(version=__version__)  # pylint: disable=undefined-variable
