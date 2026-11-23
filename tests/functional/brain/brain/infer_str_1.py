str(s)  # inferred: Const('')
str('a')  # inferred: Const('a')
str(some_object())  # inferred: Const('')
str(7**10000)  # inferred: Const('')
