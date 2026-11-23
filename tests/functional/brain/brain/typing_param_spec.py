from typing import ParamSpec

# +3: targets[0].inferred: Instance(typing.ParamSpec)
# +2: targets[0].inferred.igetattr(args): Instance(typing.ParamSpecArgs)
# +1: targets[0].inferred.igetattr(kwargs): Instance(typing.ParamSpecKwargs)
P = ParamSpec("P")
