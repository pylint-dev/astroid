# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import os
import sys
from datetime import datetime

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath(".."))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = ".rst"

# Pin the language so warning messages are identical for everyone, whatever
# the locale of the machine running the build happens to be.
language = "en"

# The master toctree document.
root_doc = "index"

# General information about the project.
project = "Astroid"
current_year = datetime.utcnow().year
contributors = "Logilab, and astroid contributors"
copyright = f"2003-{current_year}, {contributors}"

from astroid.__pkginfo__ import __version__  # noqa

release = __version__

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["media"]

# Output file base name for HTML help builder.
htmlhelp_basename = "Pylintdoc"

# -- Options for Autodoc -------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "undoc-members": True,
}
intersphinx_mapping = {
    # Use dev so that the documentation builds when we are adding support for
    # upcoming Python versions.
    "python": ("https://docs.python.org/dev", None),
}

# -- Options for cross-reference checking --------------------------------------

# Warn about every cross-reference that does not resolve. Combined with the
# ``-W`` passed by ``tox -e docs`` and by ``fail_on_warning`` in
# ``.readthedocs.yaml``, a reference to something that does not exist (or that
# is written without its module path) breaks the build instead of silently
# rendering as plain text.
nitpicky = True

# Targets that can never resolve, so that ``nitpicky`` only reports mistakes we
# can actually act on. Both halves of each pair are regexes matched in full.
#
# Keep this list short. Every entry hides a category of broken link, so add one
# only when the target genuinely cannot be documented; a public class or method
# that is merely written without its module path belongs in the docs, not here.
nitpick_ignore_regex = [
    # Private modules, private helpers and TypeVars, e.g.
    # ``astroid.nodes._base_nodes.Statement``. Autodoc prints the annotations
    # of public functions as they are written in the source, and these are not
    # part of the public API, so they have no page to link to.
    (r"py:.*", r"(?:\w+\.)*_\w+(?:\.\w+)*"),
    # Same reason, for annotations written relative to their own module, e.g.
    # ``node_classes.NodeNG``. The name Sphinx sees has no module path in it.
    (r"py:class", r"(?:arguments|node_classes|objectmodel|objects)\.\w+"),
    # ``Uninferable`` is a singleton object, not a class, so it can never be a
    # ``:class:`` target. Prose should link to :obj:`~astroid.Uninferable`.
    (r"py:class", r"Uninferable"),
    # Type aliases and base classes used unqualified in annotations. They exist
    # only to spell out signatures, and have no page of their own.
    (r"py:class", r"FrameType|InferenceContext|InferenceResult"),
    (r"py:class", r"LookupMixIn|SuccessfulInferenceResult"),
    # Public modules the API documentation does not cover yet. Deleting a line
    # here turns that module's references back on, so this doubles as a to-do.
    (r"py:class", r"astroid\.bases\.Proxy"),
    (r"py:class", r"astroid\.context\.InferenceContext"),
    (r"py:class", r"astroid\.interpreter\.objectmodel\.\w+"),
    (r"py:class", r"astroid\.manager\.AstroidManager"),
    (r"py:class", r"astroid\.nodes\.as_string\.AsStringVisitor"),
    (r"py:class", r"astroid\.objects\.DictInstance"),
    (r"py:class", r"astroid\.typing\.\w+"),
]

# -- Options for the linkcheck builder -----------------------------------------

# Checked by a scheduled workflow rather than on every pull request, because it
# needs the network and so fails for reasons that have nothing to do with a
# change.
linkcheck_ignore = [
    # Bitbucket dropped Mercurial hosting in 2020 and these two changelog
    # entries point at repositories that went with it.
    r"https://bitbucket\.org/.*",
]
