def f1(bar: str) -> None:  # blockstart_tolineno: 1
    pass

def f2(  # blockstart_tolineno: 5
       bar: str) -> None:
    pass

def f3(  # blockstart_tolineno: 10
    bar: str
) -> None:
    pass

def f4(
    bar: str
):
    pass

def f5(  # blockstart_tolineno: 19
       bar: str):
    pass
