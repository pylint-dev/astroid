# Make sure ulrlib submodules can be imported from
#
# See pylint-dev/pylint#1640 for relevant issue
from six.moves.urllib.parse import urlparse
urlparse  # inferred: FunctionDef(urllib.parse.urlparse)
