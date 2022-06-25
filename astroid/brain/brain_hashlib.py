# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.const import PY39_PLUS
from astroid.manager import AstroidManager


def _hashlib_transform():
    maybe_usedforsecurity = ", usedforsecurity=True" if PY39_PLUS else ""
    signature = f"value=''{maybe_usedforsecurity}"
    template = """
    class %(name)s(object):
      def __init__(self, %(signature)s): pass
      def digest(self):
        return %(digest)s
      def copy(self):
        return self
      def update(self, value): pass
      def hexdigest(self):
        return ''
      @property
      def name(self):
        return %(name)r
      @property
      def block_size(self):
        return 1
      @property
      def digest_size(self):
        return 1
    """
    algorithms_with_signature = dict.fromkeys(
        ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"], signature
    )
    blake2b_signature = f"data=b'', *, digest_size=64, key=b'', salt=b'', \
            person=b'', fanout=1, depth=1, leaf_size=0, node_offset=0, \
            node_depth=0, inner_size=0, last_node=False{maybe_usedforsecurity}"
    blake2s_signature = f"data=b'', *, digest_size=32, key=b'', salt=b'', \
            person=b'', fanout=1, depth=1, leaf_size=0, node_offset=0, \
            node_depth=0, inner_size=0, last_node=False{maybe_usedforsecurity}"
    new_algorithms = dict.fromkeys(
        ["sha3_224", "sha3_256", "sha3_384", "sha3_512", "shake_128", "shake_256"],
        signature,
    )
    algorithms_with_signature.update(new_algorithms)
    algorithms_with_signature.update(
        {"blake2b": blake2b_signature, "blake2s": blake2s_signature}
    )
    classes = "".join(
        template % {"name": hashfunc, "digest": 'b""', "signature": signature}
        for hashfunc, signature in algorithms_with_signature.items()
    )
    return parse(classes)


register_module_extender(AstroidManager(), "hashlib", _hashlib_transform)
