# +4: args.default_value('b'): Const(1)
# +3: args.default_value('b').value: 1
# +2: args.default_value('c'): Const(2)
# +1: args.default_value('c').value: 2
def func(a, b=1, /, c=2): pass
