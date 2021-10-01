"""Utilities for serializing and deserializing astroid Module (and it's pals).

These shouldn't be called directly from client code,
instead call `astroid.nodes.Module.dump` and `.load`.

The serialized/deserialized data is JSON-compatible.
(Converting to JSON was chosen because it has standard library support, and is
more secure than pickling the types)

Astroid types can customize serialization and deserialization by defining
`__dump__` which should return a dict of data for serializing, and
`__load__` which should fully initialize the instance from the data.
Both methods are provided a helper function for dumping or losding
non-trivial data (when in doubt, use the helper).

Because astroid types have the possibility of being circularly referenced,
object instances aren't serialized directly as values of the parent's data.
Instead, each object is given an identifier and placed in a reference mapping,
with the object's reference being used as a value in the parent's data.
Additionally, dumping and loading an object is performed in two phases so we
don't infinitely recurse.
"""

import base64
import builtins
import enum
import functools


def _dump_obj_default(instance, dumper):
    if isinstance(instance, enum.Enum):
        return {"value": instance.value}
    return {k: dumper(v) for k, v in instance.__dict__.items()}


def dump(obj, refmap, depth=0):
    """Dumps an astroid object or builtin type."""
    # @TODO: Make types for the "special" dicts and serialize them specially

    if isinstance(obj, (int, str, float, bool, type(None))):
        return obj  # JSON serializable and unambiguous

    dumper = lambda x: dump(x, refmap, depth + 1)

    if isinstance(obj, list):
        return list(map(dumper, obj))

    if isinstance(obj, (set, tuple)):
        return {
            ".class": f"{obj.__class__.__name__}",
            ".values": list(map(dumper, obj)),
        }

    if isinstance(obj, dict):
        # Serializable, but ambiguous w.r.t. dumping an object
        # If this is ever false, we can serialize it as .items()
        assert all(isinstance(k, str) for k in obj)
        return {".class": "dict", ".values": {k: dumper(v) for k, v in obj.items()}}

    if obj in {..., NotImplemented}:
        return {".class": f"{obj.__class__.__name__}"}

    if isinstance(obj, bytes):
        return {
            ".class": "bytes",
            ".value": base64.b64encode(obj).decode("ascii"),
        }

    if isinstance(obj, complex):
        return {
            ".class": "complex",
            "imag": obj.imag,
            "real": obj.real,
        }

    if id(obj) not in refmap:
        assert obj.__class__.__module__.startswith("astroid")
        # Phase 1, add the obj to the refmap
        submodule = obj.__class__.__module__.split(".")[1]
        refmap[id(obj)] = {".class": f"{submodule}.{obj.__class__.__name__}"}

        # Phase 2, actually populate the entry
        data_dumper = getattr(
            obj, "__dump__", functools.partial(_dump_obj_default, obj)
        )
        refmap[id(obj)].update(**data_dumper(dumper=dumper))

    # Stringify the id, since JSON objects must have str keys
    return {".class": "Ref", ".value": str(id(obj))}


def _load_obj_default(instance, data, loader):
    return instance.__init__(**{k: loader(v) for k, v in data.items()})


def _loadref(ref, refmap):
    import astroid

    instance_or_data = refmap[ref]
    if isinstance(instance_or_data, dict):
        data = instance_or_data
        # pop in case nodes want to just unpack the dict
        submodname, classname = data.pop(".class").split(".")
        submodule = getattr(astroid, submodname)
        cls = getattr(submodule, classname)

        if issubclass(cls, enum.Enum):
            # Enum uses __new__ to initialize :(
            refmap[ref] = cls.__new__(cls, **data)
        else:
            instance = cls.__new__(cls)
            refmap[ref] = instance

            # Phase 2, populate any fields that are or contain astroic objects
            data_loader = getattr(
                instance, "__load__", functools.partial(_load_obj_default, instance)
            )
            data_loader(data, loader=lambda x: load(x, refmap))

    return refmap[ref]


def load(data, refmap):
    loader = lambda x: load(x, refmap)

    if isinstance(data, list):
        return list(map(loader, data))

    if not isinstance(data, dict):
        return data  # Just use the deserialized int or str or whatever

    if data[".class"] == "Ref":
        return _loadref(data[".value"], refmap)

    classname = data.pop(".class")
    cls = getattr(builtins, classname)
    if cls is type(NotImplemented):
        return NotImplemented

    if cls is type(...):
        return ...

    if cls is dict:
        return {k: loader(v) for k, v in data[".values"].items()}

    if cls in {set, tuple}:
        return cls(map(loader, data[".values"]))

    if cls is complex:
        return complex(**data)

    if cls is bytes:
        return base64.b64decode(data[".values"])

    assert False, "Unhandled case!"
