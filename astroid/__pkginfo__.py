# Copyright (c) 2006-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2014 Google, Inc.
# Copyright (c) 2015-2017 Ceridwen <ceridwenv@gmail.com>
# Copyright (c) 2015 Florian Bruhin <me@the-compiler.org>
# Copyright (c) 2015 Radosław Ganczarek <radoslaw@ganczarek.in>
# Copyright (c) 2016 Moises Lopez <moylop260@vauxoo.com>
# Copyright (c) 2017 Hugo <hugovk@users.noreply.github.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2017 Calen Pennington <cale@edx.org>
# Copyright (c) 2018 Ville Skyttä <ville.skytta@iki.fi>
# Copyright (c) 2018 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2019 Uilian Ries <uilianries@gmail.com>
# Copyright (c) 2019 Thomas Hisch <t.hisch@gmail.com>
# Copyright (c) 2020-2021 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 David Gilman <davidgilman1@gmail.com>
# Copyright (c) 2020 Konrad Weihmann <kweihmann@outlook.com>
# Copyright (c) 2020 Felix Mölder <felix.moelder@uni-due.de>
# Copyright (c) 2020 Michael <michael-k@users.noreply.github.com>
# Copyright (c) 2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER

"""astroid packaging information"""

# For an official release, use dev_version = None
numversion = (2, 5, 2)
dev_version = None

version = ".".join(str(num) for num in numversion)
if dev_version is not None:
    version += "-dev" + str(dev_version)

extras_require = {}
install_requires = [
    "lazy_object_proxy>=1.4.0",
    "wrapt>=1.11,<1.13",
    'typed-ast>=1.4.0,<1.5;implementation_name== "cpython" and python_version<"3.8"',
]

# pylint: disable=redefined-builtin; why license is a builtin anyway?
license = "LGPL-2.1-or-later"

author = "Python Code Quality Authority"
author_email = "code-quality@python.org"
mailinglist = "mailto://%s" % author_email
web = "https://github.com/PyCQA/astroid"

description = "An abstract syntax tree for Python with inference support."

classifiers = [
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Software Development :: Quality Assurance",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]
