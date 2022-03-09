# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE

import sys
from typing import Optional

from astroid import nodes
from astroid.context import InferenceContext

if sys.version_info >= (3, 10):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class InferenceErrorInfo(TypedDict):
    node: nodes.NodeNG
    context: Optional[InferenceContext]
