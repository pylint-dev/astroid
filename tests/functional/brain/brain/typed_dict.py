from typing import TypedDict
# +5: bases[0].inferred: ClassDef(typing.TypedDict)
# +4: bases[0].inferred.bases[0].inferred: ClassDef(builtins.dict)
# +3: bases[0].inferred.locals.get('__call__', None): [Name(dict)]
# +2: bases[0].inferred.locals.get('__call__', None)[0]: Name(dict)
# +1: bases[0].inferred.locals.get('__call__', None)[0].name: 'dict'
class CustomTD(TypedDict):
    var: int
CustomTD(var=1)  # inferred.callable(): True
