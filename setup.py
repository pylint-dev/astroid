#!/usr/bin/env python
# Copyright (c) 2006, 2009-2010, 2012-2013 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2010-2011 Julien Jehannet <julien.jehannet@logilab.fr>
# Copyright (c) 2014-2016, 2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2017 Hugo <hugovk@users.noreply.github.com>
# Copyright (c) 2018 Ashley Whetter <ashley@awhetter.co.uk>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

# pylint: disable=W0404,W0622,W0704,W0613
"""Setup script for astroid."""
import os
from setuptools import setup, find_packages
from setuptools.command import easy_install
from setuptools.command import install_lib


real_path = os.path.realpath(__file__)
astroid_dir = os.path.dirname(real_path)
pkginfo = os.path.join(astroid_dir, "astroid", "__pkginfo__.py")

with open(pkginfo, "rb") as fobj:
    exec(compile(fobj.read(), pkginfo, "exec"), locals())

with open(os.path.join(astroid_dir, "README.rst")) as fobj:
    long_description = fobj.read()


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
        python_requires=">=3.5.*",
        install_requires=install_requires,
        extras_require=extras_require,
        packages=find_packages() + ["astroid.brain"],
        setup_requires=["pytest-runner"],
        test_suite="test",
        tests_require=["pytest"],
    )


if __name__ == "__main__":
    install()
