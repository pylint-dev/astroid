# When the first arg can't be inferred, replace yields Uninferable.
import dataclasses
dataclasses.replace(undefined_name)  # inferred: Uninferable
