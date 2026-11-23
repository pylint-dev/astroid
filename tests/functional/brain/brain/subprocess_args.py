# Make sure the args attribute exists for Popen
#
# Test for https://github.com/pylint-dev/pylint/issues/1860
import subprocess
p = subprocess.Popen(['ls'])
p  # inferred: Instance(subprocess.Popen)  # inferred.igetattr(args): List([])
