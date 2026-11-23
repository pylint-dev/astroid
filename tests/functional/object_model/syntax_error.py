try:
    x[42]
except SyntaxError as err:
   err.text  # inferred: Const('')
