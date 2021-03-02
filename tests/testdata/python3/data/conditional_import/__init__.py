
from pprint import pformat

if False:

    def dump(obj, file, protocol=None):
        pass

else:
    from functools import partial
    dump = partial(pformat, indent=0)
