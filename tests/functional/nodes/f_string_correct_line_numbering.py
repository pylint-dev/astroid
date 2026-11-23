# Test that we generate correct line numbers for f-strings.
def func_foo(arg_bar, arg_foo):
    dict_foo = {}

    # +3: last_child().last_child().lineno: 8
    # +2: last_child().lineno: 8
    # +1: lineno: 8
    f'{arg_bar.attr_bar}'
