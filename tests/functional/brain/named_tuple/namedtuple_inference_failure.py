from collections import namedtuple

def foo(fields):
   return __(namedtuple("foo", fields))  # inferred: Uninferable
