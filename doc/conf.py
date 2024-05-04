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
