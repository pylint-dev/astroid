# Originally reported in https://github.com/pylint-dev/pylint/issues/8897
#
# Test that a user-defined enum class is inferred when it subclasses
# another user-defined enum class.
from enum import StrEnum

# +3: locals: RED, __annotations__, __members__, __module__, __qualname__, _value2member_map_, name
# +2: locals['__members__'][0].items: [[Const('RED'), Name(RED)]]
# +1: locals['__members__'][0].items[0][1].name: 'RED'
class Color(StrEnum):
    RED = "red"


Color.RED.value  # inferred: Const('red')
