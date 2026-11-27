# +5: args: *, x='default'
# +4: args.is_argument('x'): True
# +3: args.kw_defaults: [Const('default')]
# +2: args.kw_defaults[0]: Const('default')
# +1: args.kw_defaults[0].value: 'default'
def func(*, x = "default"):
    pass
