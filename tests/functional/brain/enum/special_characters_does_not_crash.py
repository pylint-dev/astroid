import enum
class Example(enum.Enum):
    NULL = '\N{NULL}'
Example.NULL.value  # inferred: Const('\x00')
