# MRO computation should handle circular name rebinding.
#
# The MRO computation should resolve the cycle by falling back
# to the original class.
#
# Regression test for https://github.com/pylint-dev/pylint/issues/10821
import pdb

class PatchedPdb(pdb.Pdb):
    pass

# +1: mro: mro_circular_name_rebinding_with_gap.CustomPdb, mro_circular_name_rebinding_with_gap.PatchedPdb, pdb.Pdb, bdb.Bdb, cmd.Cmd, builtins.object
class CustomPdb(PatchedPdb):
    pass

pdb.Pdb = CustomPdb
