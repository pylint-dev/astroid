import subprocess

subprocess.check_output(['echo', 'hello']);  # inferred: Const('') | Const(b'')
