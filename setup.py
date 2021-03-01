#!/usr/bin/env python
# Copyright (c) 2006, 2009-2010, 2012-2013 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2010-2011 Julien Jehannet <julien.jehannet@logilab.fr>
# Copyright (c) 2014-2016, 2018-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2017 Hugo <hugovk@users.noreply.github.com>
# Copyright (c) 2018-2019 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2019 Enji Cooper <yaneurabeya@gmail.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 David Gilman <davidgilman1@gmail.com>
# Copyright (c) 2020 Colin Kennedy <colinvfx@gmail.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

# pylint: disable=W0404,W0622,W0613
"""Setup script for astroid."""
import os
import sys
import warnings
from setuptools import find_packages, setup
from setuptools.command import easy_install  # pylint: disable=unused-import
from setuptools.command import install_lib  # pylint: disable=unused-import

if sys.version_info.major == 3 and sys.version_info.minor <= 5:
    warnings.warn(
        "You will soon need to upgrade to python 3.6 in order to use the latest version of Astroid.",
        DeprecationWarning,
    )

real_path = os.path.realpath(__file__)
astroid_dir = os.path.dirname(real_path)
pkginfo = os.path.join(astroid_dir, "astroid", "__pkginfo__.py")

with open(pkginfo, "rb") as fobj:
    exec(compile(fobj.read(), pkginfo, "exec"), locals())

with open(os.path.join(astroid_dir, "README.rst")) as fobj:
    long_description = fobj.read()


needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest-runner"] if needs_pytest else []


def install():
    return setup(
        name="astroid",
        version=version,
        license=license,
        description=description,
        long_description=long_description,
        classifiers=classifiers,
        author=author,
        author_email=author_email,
        url=web,
        python_requires=">=3.6",
        install_requires=install_requires,
        extras_require=extras_require,
        packages=find_packages(exclude=["tests"]) + ["astroid.brain"],
        setup_requires=pytest_runner,
        test_suite="test",
        tests_require=["pytest"],
    )


if __name__ == "__main__":
    install()
