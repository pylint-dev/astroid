# dataclasses.replace with no args is a TypeError at runtime, so Uninferable.
import dataclasses
dataclasses.replace()  # inferred: Uninferable
