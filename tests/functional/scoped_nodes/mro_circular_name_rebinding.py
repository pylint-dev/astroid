# MRO computation should handle circular name rebinding.
#
# When a module-level name is rebound to a subclass of itself,
# _infer_last follows the rebinding and returns the subclass.
# The MRO computation should resolve the cycle by falling back
# to the original class.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/2967
import pdb

# +1: mro: mro_circular_name_rebinding.CustomPdb, pdb.Pdb, bdb.Bdb, cmd.Cmd, builtins.object
class CustomPdb(pdb.Pdb):
    pass

pdb.Pdb = CustomPdb
