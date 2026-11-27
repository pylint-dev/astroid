# +4: args.find_argname('x')[0]: 0
# +3: args.find_argname('x')[1]: AssignName(x)
# +2: args.is_argument('x'): True
# +1: args.is_argument('y'): True
def func(x, /, y):
    pass
