from enum import Enum
class TrickyEnum(Enum):
    name = 1
    value = 2

    def func(self):
        # +1: inferred: Instance(enum_name_and_value_members_override_dynamicclassattr.TrickyEnum.name)
        self.name
        # +1: inferred: Instance(enum_name_and_value_members_override_dynamicclassattr.TrickyEnum.value)
        self.value
# +1: inferred: Instance(enum_name_and_value_members_override_dynamicclassattr.TrickyEnum.name)
TrickyEnum.name
# +1: inferred: Instance(enum_name_and_value_members_override_dynamicclassattr.TrickyEnum.value)
TrickyEnum.value
