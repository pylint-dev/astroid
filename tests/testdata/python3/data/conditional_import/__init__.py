
import pickle

if False:

    def dump(obj, file, protocol=None):
        pass

else:
    from functools import partial
    dump = partial(pickle.dump, protocol=0)
