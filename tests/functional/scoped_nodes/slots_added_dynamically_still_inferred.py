# +2: inferred: ClassDef(slots_added_dynamically_still_inferred.NodeBase)
# +1: inferred.slots: a, b, c
class NodeBase(object):
    __slots__ = "a", "b"

    if Options.isFullCompat():
        __slots__ += ("c",)
