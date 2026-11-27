@f(a=2,
   b=3)
def g1(x):  # fromlineno: 3  # tolineno: 4
    print(x)

@f(a=2,
   b=3,
)
def g2():  # fromlineno: 9  # tolineno: 10
    pass
